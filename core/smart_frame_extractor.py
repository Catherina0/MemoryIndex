import cv2
import numpy as np
import shutil
from pathlib import Path
import subprocess
import logging
from typing import List, Dict, Optional, Tuple, Any
import os

class SmartFrameExtractor:
    def __init__(self, 
                 fps: float = 2.0,
                 diff_threshold: float = 3.0,
                 static_threshold: float = 1.0,
                 static_duration_frames: int = 3,
                 enable_fusion: bool = True,
                 preprocessing_config: Dict = None,
                 debug_mode: bool = False):
        
        self.fps = fps
        self.diff_threshold = diff_threshold
        self.static_threshold = static_threshold
        self.static_duration_frames = static_duration_frames
        self.enable_fusion = enable_fusion
        self.debug_mode = debug_mode
        self.preprocessing_config = preprocessing_config or {
            'grayscale': True,
            'denoise': 'gaussian', # gaussian, bilateral
            'clahe': True,
            'adaptive_binary': False, # strictly for "black text on white"
            'unsharp_mask': False
        }
        self.logger = logging.getLogger("SmartFrameExtractor")

    def _get_frame_diff_score(self, img1: np.ndarray, img2: np.ndarray) -> float:
        """
        Improved change detection (Grid-Max Strategy):
        Instead of global average, we measure change in small grid blocks.
        This allows detecting small text changes (subtitles/bullets) even if 90% of screen is static.
        """
        # 1. Resize to reasonable size (512 width) - larger than before
        target_size = (512, 288)
        
        # Convert to grayscale
        if len(img1.shape) == 3: g1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        else: g1 = img1
            
        if len(img2.shape) == 3: g2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
        else: g2 = img2

        g1 = cv2.resize(g1, target_size, interpolation=cv2.INTER_AREA)
        g2 = cv2.resize(g2, target_size, interpolation=cv2.INTER_AREA)

        # 2. Pixel-wise Diff & Noise Threshold
        diff = cv2.absdiff(g1, g2)
        # Ignore signal noise < 15 intensity
        _, thresh = cv2.threshold(diff, 15, 255, cv2.THRESH_TOZERO)
        
        # 3. Grid-based Max Pooling (8x8 Grid)
        # We resize the thresholded diff map to 8x8.
        # INTER_AREA does averaging. So each pixel in 8x8 represents mean diff of that block.
        grid_h, grid_w = 8, 8
        mini_diff = cv2.resize(thresh, (grid_w, grid_h), interpolation=cv2.INTER_AREA)
        
        # 4. Score is the MAXIMUM change found in any single grid block
        # For full page turn -> All blocks high -> Max high
        # For one sentence change -> One block high -> Max high
        score = np.max(mini_diff)
        
        return float(score)

    def _preprocess_frame(self, img: np.ndarray) -> np.ndarray:
        """
        Apply configured preprocessing pipeline on ROI
        """
        out = img.copy()
        
        # 1. Grayscale
        if self.preprocessing_config.get('grayscale', True) and len(out.shape) == 3:
            out = cv2.cvtColor(out, cv2.COLOR_BGR2GRAY)
        
        # 2. Denoise
        denoise_method = self.preprocessing_config.get('denoise', 'gaussian')
        if denoise_method == 'gaussian':
            out = cv2.GaussianBlur(out, (3, 3), 0)
        elif denoise_method == 'bilateral':
            # Bilateral works better on color, but we might be gray here. 
            # If gray, it still works.
            out = cv2.bilateralFilter(out, 5, 75, 75)
            
        # 3. CLAHE
        if self.preprocessing_config.get('clahe', True):
            # Apply CLAHE
            # If color, applying to L channel is better, but we are likely gray here
            if len(out.shape) == 3:
                # Convert to LAB, apply to L, merge back
                lab = cv2.cvtColor(out, cv2.COLOR_BGR2LAB)
                l, a, b = cv2.split(lab)
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                cl = clahe.apply(l)
                limg = cv2.merge((cl, a, b))
                out = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
            else:
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                out = clahe.apply(out)
                
        # 4. Adaptive Binary
        if self.preprocessing_config.get('adaptive_binary', False):
            if len(out.shape) == 3:
               out = cv2.cvtColor(out, cv2.COLOR_BGR2GRAY) 
            out = cv2.adaptiveThreshold(out, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                        cv2.THRESH_BINARY, 11, 2)

        # Optional: Unsharp Mask
        if self.preprocessing_config.get('unsharp_mask', False):
             gaussian = cv2.GaussianBlur(out, (0, 0), 2.0)
             out = cv2.addWeighted(out, 1.5, gaussian, -0.5, 0)

        return out


    def _calculate_laplacian_variance(self, img: np.ndarray) -> float:
        """Calculate Laplacian variance (sharpness score)."""
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img
        return cv2.Laplacian(gray, cv2.CV_64F).var()

    def _fuse_frames_advanced(self, frames: List[np.ndarray]) -> np.ndarray:
        """
        Advanced fusion logic:
        1. Check background brightness.
        2. If likely White-on-Black (dark bg) -> Max Fusion.
        3. If likely Black-on-White (light bg) -> Min Fusion.
        4. Fallback -> Median.
        """
        if not frames: return None
        if len(frames) == 1: return frames[0]

        stack = np.stack(frames, axis=0)
        
        # Analyze brightness of the middle frame to decide strategy
        mid_frame = frames[len(frames)//2]
        if len(mid_frame.shape) == 3:
            gray_mid = cv2.cvtColor(mid_frame, cv2.COLOR_BGR2GRAY)
        else:
            gray_mid = mid_frame
            
        avg_brightness = np.mean(gray_mid)
        
        # Heuristic: 
        # > 127 => Light Background => Text likely dark => Use MIN to keep ink
        # < 127 => Dark Background  => Text likely light => Use MAX to keep light
        
        if avg_brightness > 127:
            # Light BG: Min fusion (erode noise, keep dark text)
            fused = np.min(stack, axis=0).astype(np.uint8)
        else:
            # Dark BG: Max fusion (dilate noise, keep light text)
            fused = np.max(stack, axis=0).astype(np.uint8)
            
        return fused

    def extract(self, video_path: Path, output_dir: Path, temp_dir: Path) -> List[Dict]:
        """
        Execute smart extraction with Hysteresis and Stability Wait.
        """
        if output_dir.exists():
            shutil.rmtree(output_dir)
        output_dir.mkdir(parents=True)
        
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        temp_dir.mkdir(parents=True)
        
        print(f"🎬 [SmartExtract] Sampling frames at {self.fps} fps...")
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(video_path),
            "-vf", f"fps={self.fps}",
            str(temp_dir / "raw_%06d.png")
        ]
        subprocess.run(cmd, check=True)
        
        raw_files = sorted(list(temp_dir.glob("raw_*.png")))
        if not raw_files:
            return []

        print(f"🔍 [SmartExtract] Analyzing {len(raw_files)} candidate frames (Hysteresis Mode)...")
        
        processed_frames_meta = []
        
        # State Machine Variables
        # STATE: "STABLE" or "TRANSITION"
        state = "STABLE"
        
        last_stable_frame = cv2.imread(str(raw_files[0])) # The reference for change detection
        
        # Initially save the first frame
        init_meta = self._save_frame(last_stable_frame, 1, 0.0, output_dir, is_fused=False)
        processed_frames_meta.append(init_meta)
        
        transition_buffer = [] # Buffer for frames while in transition
        stable_counter = 0     # Count consecutive frames below T_exit
        
        for i in range(1, len(raw_files)):
            curr_path = raw_files[i]
            curr_img = cv2.imread(str(curr_path))
            curr_idx = i + 1
            
            # Compare current to the LAST CONFIRMED STABLE FRAME to detect entry
            # Compare current to PREVIOUS FRAME to detect exit (stability)
            
            diff_from_stable = self._get_frame_diff_score(curr_img, last_stable_frame)
            
            if state == "STABLE":
                if diff_from_stable > self.diff_threshold: # T_enter
                    # Enter Transition
                    state = "TRANSITION"
                    transition_buffer = [curr_img]
                    stable_counter = 0
                    # print(f"  --> Unstable at frame {curr_idx} (diff={diff_from_stable:.1f})")
                else:
                    # Still stable, nothing to do (ignoring minor drift)
                    pass
                    
            elif state == "TRANSITION":
                transition_buffer.append(curr_img)
                
                # Check consecutive stability (T_exit)
                # Compare against the PREVIOUS frame in buffer (immediate predecessor)
                prev_in_buffer = transition_buffer[-2]
                diff_step = self._get_frame_diff_score(curr_img, prev_in_buffer)
                
                if diff_step < self.static_threshold: # T_exit
                    stable_counter += 1
                else:
                    stable_counter = 0
                    
                if stable_counter >= self.static_duration_frames:
                    # Exiting Transition -> STABILIZED
                    state = "STABLE"
                    
                    # Process the buffer to find the best frame
                    # We only care about the end of the buffer (the stable part) + a bit of history
                    # But if we want to support "gradual fade", we might want to fuse the stable part.
                    
                    stable_segment = transition_buffer[-self.static_duration_frames:]
                    
                    # Decide: Fuse or Pick Best?
                    # Check if the stable segment is extremely static (pixel diff near 0)
                    segment_diff = self._get_frame_diff_score(stable_segment[0], stable_segment[-1])
                    
                    final_img = None
                    is_fused = False
                    reason = "sharpest"
                    
                    if self.enable_fusion and segment_diff < 1.0: # Very tight stability
                        # Perform fusion
                        final_img = self._fuse_frames_advanced(stable_segment)
                        is_fused = True
                        reason = "fused"
                    else:
                        # Pick the sharpest frame from the stable segment
                        best_var = -1.0
                        best_frame = None
                        for f in stable_segment:
                            var = self._calculate_laplacian_variance(f)
                            if var > best_var:
                                best_var = var
                                best_frame = f
                        final_img = best_frame
                    
                    # Double check: Is this new result significantly different from the PREVIOUS saved frame?
                    # Avoid saving duplicate if the transition was just a false alarm or returned to same state
                    # We use a lower threshold here (hardcoded 1.0) to capture even subtle valid updates (like new bullet points)
                    # even if the stability threshold was set higher (e.g. 3.0)
                    
                    diff_from_last_saved = self._get_frame_diff_score(final_img, last_stable_frame)
                    
                    SAVE_THRESHOLD = 1.0  # Always strictly capture > 1.0 change
                    
                    if diff_from_last_saved > SAVE_THRESHOLD:
                        meta = self._save_frame(final_img, curr_idx, diff_from_stable, output_dir, is_fused=is_fused)
                        processed_frames_meta.append(meta)
                        last_stable_frame = final_img
                        print(f"  📸 Capture change at frame {curr_idx}: {reason} (score={diff_from_last_saved:.1f})")
                    else:
                        # It went back to the old state? Or change was subtle. Update reference anyway?
                        # If we don't update reference, we might drift. Let's update.
                        # But we don't save new file.
                        last_stable_frame = final_img 
                        
                    transition_buffer = []
                    stable_counter = 0

        # Cleanup
        if not self.debug_mode:
             shutil.rmtree(temp_dir)

        print(f"✅ [SmartExtract] Retained {len(processed_frames_meta)} frames (from {len(raw_files)}).")
        return processed_frames_meta


    def _save_frame(self, img: np.ndarray, original_idx: int, score: float, output_dir: Path, is_fused: bool = False) -> Dict:
        # Apply preprocessing pipeline
        final_img = self._preprocess_frame(img)
        
        # Name
        out_name = f"frame_{original_idx:06d}.png"
        out_path = output_dir / out_name
        cv2.imwrite(str(out_path), final_img)
        
        meta = {
            'file_name': out_name,
            'time_sec': (original_idx - 1) / self.fps,
            'is_fused': is_fused,
            'score': score
        }
        return meta
