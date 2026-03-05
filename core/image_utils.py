
import os
import math
from pathlib import Path
from typing import List, Tuple
from PIL import Image

def split_long_image(
    image_path: Path, 
    max_height: int = 3000, 
    overlap: int = 200,
    output_dir: Path = None
) -> List[Path]:
    """
    Check if an image is too long and split it into chunks if necessary.
    
    Args:
        image_path: Path to the image file.
        max_height: Maximum height for each chunk.
        overlap: Overlap height between chunks to prevent cutting lines of text.
        output_dir: Directory to save chunks. If None, uses the image's parent dir.
        
    Returns:
        List of paths to the image chunks. If no split needed, returns list with original path.
    """
    img_path = Path(image_path)
    if not img_path.exists():
        return []

    try:
        with Image.open(img_path) as img:
            width, height = img.size
            if height <= max_height:
                return [img_path]
            
            if output_dir is None:
                output_dir = img_path.parent
            else:
                output_dir = Path(output_dir)
                output_dir.mkdir(parents=True, exist_ok=True)

            num_chunks = math.ceil((height - overlap) / (max_height - overlap))
            if num_chunks <= 1:
                return [img_path]
            
            chunk_paths = []
            stem = img_path.stem
            ext = img_path.suffix

            for i in range(num_chunks):
                top = i * (max_height - overlap)
                bottom = min(top + max_height, height)
                
                # Verify we don't go backwards or get stuck
                if top >= height:
                    break
                
                # Crop
                chunk = img.crop((0, top, width, bottom))
                chunk_filename = f"{stem}_chunk_{i}{ext}"
                chunk_path = output_dir / chunk_filename
                
                # Save chunk
                chunk.save(chunk_path)
                chunk_paths.append(chunk_path)
            
            return chunk_paths

    except Exception as e:
        print(f"⚠️  Error processing image {img_path}: {e}")
        return [img_path]
