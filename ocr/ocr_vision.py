"""
ocr_vision.py
Apple Vision Framework OCR Python 包装器

提供与 PaddleOCR 兼容的接口，使用 Apple 原生 OCR 引擎（macOS 10.15+）
优势：
  - 无需下载模型
  - 原生优化，速度快
  - 支持多语言（中文、日文、韩文等）
  - 零依赖（仅需系统自带 Swift）
"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import List, Tuple, Optional

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("⚠️  Vision OCR Warning: PIL (Pillow) not installed. Long image handling disabled.")

# Swift 脚本路径
VISION_OCR_SCRIPT = Path(__file__).parent / "vision_ocr.swift"
# 编译后的二进制文件路径
VISION_OCR_BIN = Path(__file__).parent / "vision_ocr_bin"
# 画布裁剪最大尺寸（超过此尺寸将进行裁剪识别）
MAX_CANVAS_SIZE = 3000


class VisionOCR:
    """
    Apple Vision Framework OCR 封装类
    
    接口设计与 PaddleOCR 保持一致，方便替换使用
    """
    
    def __init__(
        self,
        lang: str = "ch",
        recognition_level: str = "accurate",
        use_language_correction: bool = True,
        **kwargs  # 兼容 PaddleOCR 的其他参数
    ):
        """
        初始化 Vision OCR
        
        Args:
            lang: 语言代码，'ch'=中英文混合, 'en'=英文, 'japan'=日文等
            recognition_level: 识别精度 'fast' 或 'accurate'（默认）
            use_language_correction: 是否启用语言纠错（默认 True）
            **kwargs: 兼容参数（如 use_gpu, det_model 等，此处忽略）
        """
        # 检查 macOS 环境
        if not self._check_macos():
            raise RuntimeError("VisionOCR 仅支持 macOS 10.15 及以上版本")
        
        # 检查 Swift 脚本
        if not VISION_OCR_SCRIPT.exists():
            raise FileNotFoundError(f"未找到 Swift OCR 脚本: {VISION_OCR_SCRIPT}")
            
        # 尝试编译 Swift 脚本以提升性能
        self._compile_swift_script()
        
        # 语言映射：PaddleOCR 风格 -> Vision Framework 风格
        lang_map = {
            "ch": ["zh-Hans", "en-US"],      # 中文+英文
            "chinese_cht": ["zh-Hant", "en-US"],  # 繁体中文+英文
            "en": ["en-US"],
            "japan": ["ja-JP", "en-US"],
            "korean": ["ko-KR", "en-US"],
            "german": ["de-DE"],
            "french": ["fr-FR"],
        }
        
        self.languages = lang_map.get(lang, ["zh-Hans", "en-US"])
        self.recognition_level = recognition_level
        self.use_language_correction = use_language_correction
    
    def _compile_swift_script(self):
        """若需要，编译 Swift 脚本以提升性能"""
        try:
            # 检查是否需要重新编译：如果二进制不存在，或者源码比二进制新
            should_compile = False
            if not VISION_OCR_BIN.exists():
                should_compile = True
            elif VISION_OCR_SCRIPT.stat().st_mtime > VISION_OCR_BIN.stat().st_mtime:
                should_compile = True
                
            if should_compile:
                print(f"ℹ️  Vision OCR: Compiling Swift script for performance...")
                # swiftc -o vision_ocr_bin vision_ocr.swift
                subprocess.run(
                    ["swiftc", str(VISION_OCR_SCRIPT), "-o", str(VISION_OCR_BIN)],
                    check=True,
                    capture_output=True
                )
        except Exception as e:
            print(f"⚠️  Vision OCR Compilation Failed: {e}. Fallback to interpreter mode.")
            if VISION_OCR_BIN.exists():
                try:
                    VISION_OCR_BIN.unlink()
                except:
                    pass

    def _ocr_tiled(self, img, width: int, height: int, **kwargs) -> List:
        """
        切分并识别大图
        
        Args:
            img: PIL Image 对象
            width: 原图宽度
            height: 原图高度
            **kwargs: 透传参数
        
        Returns:
            合并后的识别结果
        """
        rec_texts = []
        rec_scores = []
        
        print(f"ℹ️  Vision OCR: 检测到大图 ({width}x{height})，启动切片识别模式...")
        
        # Calculate grid steps
        v_steps = (height + MAX_CANVAS_SIZE - 1) // MAX_CANVAS_SIZE
        h_steps = (width + MAX_CANVAS_SIZE - 1) // MAX_CANVAS_SIZE
        
        total_chunks = v_steps * h_steps
        current_chunk = 0
        
        # 使用 TemporaryDirectory 确保即使崩溃也能清理临时文件（虽然 hard kill 可能不行，但比单个文件好管理）
        with tempfile.TemporaryDirectory(prefix="ocr_vision_tiled_") as temp_dir:
            for i in range(v_steps):
                for j in range(h_steps):
                    current_chunk += 1
                    left = j * MAX_CANVAS_SIZE
                    upper = i * MAX_CANVAS_SIZE
                    right = min((j + 1) * MAX_CANVAS_SIZE, width)
                    lower = min((i + 1) * MAX_CANVAS_SIZE, height)
                    
                    print(f"    Processing chunk {current_chunk}/{total_chunks}: ({left}, {upper}) -> ({right}, {lower})")
                    
                    # Crop region
                    region = img.crop((left, upper, right, lower))
                    
                    # Save to temp file inside the temp directory
                    tmp_filename = f"chunk_{i}_{j}.png"
                    tmp_path = os.path.join(temp_dir, tmp_filename)
                    
                    try:
                        region.save(tmp_path, format="PNG")
                        
                        # Recursive call (minimal overhead)
                        chunk_res = self.ocr(tmp_path, **kwargs)
                        
                        if chunk_res and chunk_res[0]:
                            chunk_texts = chunk_res[0].get("rec_texts", [])
                            chunk_scores = chunk_res[0].get("rec_scores", [])
                            
                            rec_texts.extend(chunk_texts)
                            rec_scores.extend(chunk_scores)
                            
                    except Exception as e:
                        print(f"⚠️  Vision OCR Chunk Error: {e}")
                    
                    # (可选)处理完一个切片后立即删除文件以释放空间，虽然 temp_dir 最终会清理
                    if os.path.exists(tmp_path):
                        try:
                            os.unlink(tmp_path)
                        except:
                            pass
                        
        if rec_texts:
            return [{
                "rec_texts": rec_texts,
                "rec_scores": rec_scores
            }]
        return [[]]

    def _check_macos(self) -> bool:
        """检查是否在 macOS 环境"""
        import platform
        return platform.system() == "Darwin"
    
    def ocr(
        self,
        image_path: str,
        cls: bool = True,  # 兼容参数（Vision 自动处理方向）
        **kwargs
    ) -> List:
        """
        对图片进行 OCR 识别
        
        Args:
            image_path: 图片路径
            cls: 方向分类（兼容参数，Vision 自动处理）
            **kwargs: 其他兼容参数
        
        Returns:
            识别结果（兼容 PaddleOCR 3.x 格式）
            格式: [{"rec_texts": [...], "rec_scores": [...]}]
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"图片不存在: {image_path}")

        # 大图自动切片逻辑
        if PIL_AVAILABLE:
            try:
                with Image.open(image_path) as img:
                    width, height = img.size
                    
                    if width > MAX_CANVAS_SIZE or height > MAX_CANVAS_SIZE:
                        # 递归调用时避免无限循环（通过检查临时文件后缀或其他机制，或者直接在 _ocr_tiled 里面手动分割）
                        # 这里我们直接调用 _ocr_tiled，它使用 crop 和 tempfile
                        # 只有原始大图才会进这个 IF 分支
                        return self._ocr_tiled(img, width, height, **kwargs)
            except Exception as e:
                # 常见错误：非图片文件、格式不支持等
                # 不阻断流程，尝试直接传给 swift
                if "DecompressionBombError" in str(e):
                    print(f"⚠️  Vision OCR: 图片极大 (DecompressionBombError)，尝试直接处理...")
                else:
                    # print(f"⚠️  Vision OCR Warning: PIL Check Failed: {e}")
                    pass
        
        # 构建命令：优先使用编译后的二进制以提升性能
        cmd = []
        if VISION_OCR_BIN.exists() and os.access(VISION_OCR_BIN, os.X_OK):
            cmd = [str(VISION_OCR_BIN)]
        else:
            # Fallback to interpreter
            cmd = ["swift", str(VISION_OCR_SCRIPT)]
            
        cmd.extend([
            str(image_path),
            "--lang", ",".join(self.languages),
            "--level", self.recognition_level
        ])
        
        if not self.use_language_correction:
            cmd.append("--no-correction")
        
        try:
            # 执行 Swift 脚本，捕获标准输出作为识别结果
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,  # 增加超时时间到 120 秒
                check=False
            )
            
            if result.returncode != 0 and result.returncode != 1:
                # returncode=1 可能只是没识别到文本
                print(f"⚠️  Vision OCR 警告: {result.stderr.strip()}")
            
            # 解析输出（每行一个识别文本）
            lines = result.stdout.strip().split('\n')
            rec_texts = [line for line in lines if line.strip()]
            
            # 生成置信度（Vision 不提供置信度，默认给 0.9）
            rec_scores = [0.9] * len(rec_texts)
            
            # 返回 PaddleOCR 3.x 兼容格式
            if rec_texts:
                return [{
                    "rec_texts": rec_texts,
                    "rec_scores": rec_scores
                }]
            else:
                return [[]]  # 未识别到文本
        
        except subprocess.TimeoutExpired:
            print(f"⚠️  Vision OCR 超时: {image_path}")
            return [[]]
        except Exception as e:
            print(f"⚠️  Vision OCR 错误: {e}")
            return [[]]


def init_vision_ocr(lang="ch", recognition_level="accurate", **kwargs) -> VisionOCR:
    """
    初始化 Vision OCR（快捷函数）
    
    Args:
        lang: 语言代码
        recognition_level: 识别精度 'fast' 或 'accurate'
        **kwargs: 其他兼容参数
    
    Returns:
        VisionOCR 实例
    """
    return VisionOCR(lang=lang, recognition_level=recognition_level, **kwargs)


def ocr_image_vision(
    ocr: VisionOCR,
    image_path: str,
    min_score: float = 0.3,
    debug: bool = False,
    **kwargs
) -> str:
    """
    对单张图片做 OCR（兼容 ocr_utils.ocr_image 接口）
    
    Args:
        ocr: VisionOCR 实例
        image_path: 图片路径
        min_score: 最小置信度（Vision 不提供置信度，此参数忽略）
        debug: 是否显示调试信息
        **kwargs: 其他兼容参数
    
    Returns:
        识别到的文本（按行拼接）
    """
    try:
        result = ocr.ocr(image_path)
        
        if not result or not result[0]:
            return ""
        
        item = result[0]
        
        if isinstance(item, dict):
            rec_texts = item.get('rec_texts', [])
            
            if debug:
                rec_scores = item.get('rec_scores', [])
                for text, score in zip(rec_texts, rec_scores):
                    print(f"    [Vision OCR] {text} (置信度: {score:.2f})")
            
            return '\n'.join(rec_texts)
        
        return ""
    
    except Exception as e:
        if debug:
            print(f"    [Vision OCR 错误] {e}")
        return ""


def ocr_folder_vision(
    ocr: VisionOCR,
    frames_dir: Path,
    output_path: Path,
    interval: float = 2.0,
    debug: bool = False,
    **kwargs
) -> str:
    """
    批量处理文件夹中的图片（兼容 ocr_utils.ocr_folder_to_text 接口）
    
    Args:
        ocr: VisionOCR 实例
        frames_dir: 图片文件夹路径
        output_path: 输出文件路径
        interval: 时间间隔（用于日志输出）
        debug: 是否显示调试信息
        **kwargs: 其他兼容参数
    
    Returns:
        合并后的 OCR 文本
    """
    from tqdm import tqdm
    
    frames = sorted(frames_dir.glob("frame_*.png"))
    
    if not frames:
        print(f"⚠️  未找到图片: {frames_dir}")
        return ""
    
    all_texts = []
    
    print(f"📖 Vision OCR 识别中... (共 {len(frames)} 帧)")
    
    for frame_path in tqdm(frames, desc="Vision OCR", ncols=80):
        text = ocr_image_vision(ocr, str(frame_path), debug=debug)
        if text.strip():
            all_texts.append(text)
    
    # 合并文本
    merged_text = '\n'.join(all_texts)
    
    # 保存到文件
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(merged_text, encoding='utf-8')
        print(f"✅ OCR 文本已保存: {output_path}")
    
    return merged_text


# ========== 便捷导出 ==========
__all__ = [
    'VisionOCR',
    'init_vision_ocr',
    'ocr_image_vision',
    'ocr_folder_vision',
]
