#!/usr/bin/env python3
"""
OCR 多进程并行处理模块
提升 Apple Silicon Mac 上的 CPU 利用率和处理速度
"""

import os
import sys
import logging
import warnings
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
from multiprocessing import Pool, cpu_count
from pathlib import Path
from tqdm import tqdm
import tempfile
from PIL import Image, ImageEnhance

# 抑制 PaddleOCR/PaddleX 日志
os.environ['PADDLEX_DISABLE_PRINT'] = '1'
os.environ['DISABLE_MODEL_SOURCE_CHECK'] = 'True'
warnings.filterwarnings('ignore')
logging.getLogger('ppocr').setLevel(logging.ERROR)
logging.getLogger('paddle').setLevel(logging.ERROR)
logging.getLogger('paddlex').setLevel(logging.ERROR)

from paddleocr import PaddleOCR


def preprocess_image(image_path, enhance_contrast=True, roi_bottom_only=False, bottom_ratio=0.25):
    """图像预处理（与 ocr_utils.py 相同）"""
    img = Image.open(image_path)
    
    if roi_bottom_only:
        width, height = img.size
        top = int(height * (1 - bottom_ratio))
        img = img.crop((0, top, width, height))
    
    if enhance_contrast:
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.5)
        
        sharpener = ImageEnhance.Sharpness(img)
        img = sharpener.enhance(1.3)
    
    return img


def _suppress_paddle_logs():
    """在子进程中抑制 PaddleOCR/PaddleX 日志"""
    import os
    import sys
    import logging
    import warnings
    
    os.environ['PADDLEX_DISABLE_PRINT'] = '1'
    os.environ['DISABLE_MODEL_SOURCE_CHECK'] = 'True'
    os.environ['FLAGS_allocator_strategy'] = 'auto_growth'
    
    warnings.filterwarnings('ignore')
    logging.getLogger('ppocr').setLevel(logging.ERROR)
    logging.getLogger('paddle').setLevel(logging.ERROR)
    logging.getLogger('paddlex').setLevel(logging.ERROR)
    
    # 禁用 PaddleX 的连接检查输出
    class NullWriter:
        def write(self, s): pass
        def flush(self): pass
    
    return NullWriter()


def _create_ocr_silent():
    """静默创建 OCR 实例，抑制所有日志输出"""
    _suppress_paddle_logs()
    
    # 临时重定向 stdout/stderr
    import sys
    from io import StringIO
    
    old_stdout, old_stderr = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = StringIO(), StringIO()
    
    try:
        ocr = PaddleOCR(
            lang='ch',
            use_textline_orientation=True,
            text_det_thresh=0.2,
            text_det_box_thresh=0.4,
            text_det_unclip_ratio=2.2,
            text_recognition_batch_size=6
        )
    finally:
        sys.stdout, sys.stderr = old_stdout, old_stderr
    
    return ocr


def process_single_image_worker(args):
    """
    工作进程：处理单张图片
    每个进程创建自己的 OCR 实例以避免共享问题
    """
    image_path, min_score, use_preprocessing, hybrid_mode = args
    
    # 在子进程中静默创建 OCR 实例
    ocr = _create_ocr_silent()
    
    try:
        all_texts = set()
        
        if hybrid_mode:
            # 混合模式：字幕区 + 全画面
            # 第一次：字幕区
            if use_preprocessing:
                processed_subtitle = preprocess_image(
                    image_path,
                    enhance_contrast=True,
                    roi_bottom_only=True,
                    bottom_ratio=0.25
                )
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    processed_subtitle.save(tmp.name)
                    temp_path_subtitle = tmp.name
                
                try:
                    result = ocr.ocr(temp_path_subtitle)
                    texts = _extract_texts(result, min_score)
                    all_texts.update(texts)
                finally:
                    import os
                    os.unlink(temp_path_subtitle)
            
            # 第二次：全画面
            if use_preprocessing:
                processed_full = preprocess_image(
                    image_path,
                    enhance_contrast=True,
                    roi_bottom_only=False
                )
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    processed_full.save(tmp.name)
                    temp_path_full = tmp.name
                
                try:
                    result = ocr.ocr(temp_path_full)
                    texts = _extract_texts(result, min_score)
                    all_texts.update(texts)
                finally:
                    import os
                    os.unlink(temp_path_full)
            else:
                result = ocr.ocr(str(image_path))
                texts = _extract_texts(result, min_score)
                all_texts.update(texts)
            
            return '\n'.join(sorted(all_texts)) if all_texts else ""
        
        else:
            # 单一模式
            if use_preprocessing:
                processed_img = preprocess_image(
                    image_path,
                    enhance_contrast=True,
                    roi_bottom_only=True,
                    bottom_ratio=0.25
                )
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    processed_img.save(tmp.name)
                    temp_path = tmp.name
                
                try:
                    result = ocr.ocr(temp_path)
                finally:
                    import os
                    os.unlink(temp_path)
            else:
                result = ocr.ocr(str(image_path))
            
            texts = _extract_texts(result, min_score)
            return '\n'.join(texts)
            
    except Exception as e:
        print(f"⚠️  处理失败 {image_path}: {e}")
        return ""


def _extract_texts(result, min_score):
    """从 OCR 结果中提取文本"""
    texts = []
    
    if result and len(result) > 0:
        item = result[0]
        
        if isinstance(item, dict):
            rec_texts = item.get('rec_texts', [])
            rec_scores = item.get('rec_scores', [])
            
            for text, score in zip(rec_texts, rec_scores):
                if score >= min_score:
                    texts.append(text)
    
    return texts


def ocr_folder_parallel(frames_dir: str, 
                       min_score: float = 0.3,
                       num_workers: int = None,
                       use_preprocessing: bool = True,
                       hybrid_mode: bool = True) -> str:
    """
    多进程并行处理整个目录的图片
    
    参数:
        frames_dir: 帧图片目录
        min_score: 最小置信度阈值
        num_workers: 工作进程数（None=自动检测，推荐 cpu_count()//2）
                    可通过环境变量 OCR_WORKERS 设置
        use_preprocessing: 是否使用图像预处理
        hybrid_mode: 混合模式（字幕区 + 全画面）
    
    返回:
        拼接后的文本
    """
    # 获取所有图片文件
    image_files = sorted(Path(frames_dir).glob("*.png"))
    
    if not image_files:
        print(f"⚠️  未找到图片文件: {frames_dir}")
        return ""
    
    # 确定工作进程数
    if num_workers is None:
        # 优先从环境变量读取
        import os
        env_workers = os.environ.get('OCR_WORKERS')
        if env_workers and env_workers.lower() != 'auto':
            try:
                num_workers = int(env_workers)
            except ValueError:
                pass
        
        # 如果环境变量未设置或为 'auto'，使用默认值
        if num_workers is None:
            # Apple Silicon: 使用一半的核心（避免过热）
            total_cores = cpu_count()
            num_workers = max(1, total_cores // 2)
    
    # 打印实际使用的工作进程数
    print(f"🔧 工作进程: {num_workers}")
    
    # 准备参数
    args_list = [
        (img, min_score, use_preprocessing, hybrid_mode) 
        for img in image_files
    ]
    
    # 多进程处理
    all_texts = []
    with Pool(processes=num_workers) as pool:
        results = list(tqdm(
            pool.imap(process_single_image_worker, args_list),
            total=len(args_list),
            desc="📄 OCR处理",
            unit="帧",
            ncols=80
        ))
        
        # 收集非空文本
        all_texts = [text for text in results if text.strip()]
    
    # 简单去重（相邻相同的文本）
    unique_texts = []
    prev_text = ""
    for text in all_texts:
        if text != prev_text:
            unique_texts.append(text)
            prev_text = text
    
    return '\n'.join(unique_texts)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        frames_dir = sys.argv[1]
        result = ocr_folder_parallel(
            frames_dir,
            min_score=0.3,
            num_workers=5  # Apple Silicon 推荐
        )
        print(f"\n识别结果预览（前200字符）：")
        print(result[:200])
    else:
        print("用法: python ocr_parallel.py <frames_dir>")
        print("示例: python ocr_parallel.py output/test/frames")
