#!/usr/bin/env python3
"""
OCR 并行处理模块
使用线程池代替进程池，避免 macOS 上的子进程退出弹窗问题
"""

import os
import sys
import logging
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from tqdm import tqdm
import tempfile
from PIL import Image, ImageEnhance
import threading

# 抑制 PaddleOCR/PaddleX 日志
os.environ['PADDLEX_DISABLE_PRINT'] = '1'
os.environ['DISABLE_MODEL_SOURCE_CHECK'] = 'True'
os.environ['FLAGS_allocator_strategy'] = 'auto_growth'
os.environ['GLOG_minloglevel'] = '3'
warnings.filterwarnings('ignore')
logging.getLogger('ppocr').setLevel(logging.ERROR)
logging.getLogger('paddle').setLevel(logging.ERROR)
logging.getLogger('paddlex').setLevel(logging.ERROR)

# PaddleOCR 懒加载：仅在实际使用时导入，避免未安装时模块级报错

# 线程本地存储，每个线程维护自己的 OCR 实例
_thread_local = threading.local()


def preprocess_image(image_path, enhance_contrast=True, roi_bottom_only=False, bottom_ratio=0.25):
    """图像预处理"""
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


def _get_ocr_instance():
    """获取线程本地的 OCR 实例（懒加载）"""
    if not hasattr(_thread_local, 'ocr'):
        # 懒加载 PaddleOCR，仅在调用时导入
        try:
            from paddleocr import PaddleOCR
        except ImportError as e:
            raise ImportError(f"PaddleOCR 未安装，无法使用并行 OCR: {e}") from e

        # 静默创建 OCR 实例
        from io import StringIO
        old_stdout, old_stderr = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = StringIO(), StringIO()
        
        try:
            _thread_local.ocr = PaddleOCR(
                lang='ch',
                use_textline_orientation=True,
                text_det_thresh=0.2,
                text_det_box_thresh=0.4,
                text_det_unclip_ratio=2.2,
                text_recognition_batch_size=6
            )
        finally:
            sys.stdout, sys.stderr = old_stdout, old_stderr
    
    return _thread_local.ocr


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


def process_single_image(image_path, min_score, use_preprocessing, hybrid_mode):
    """
    处理单张图片（线程安全）
    """
    ocr = _get_ocr_instance()
    
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
                    os.unlink(temp_path)
            else:
                result = ocr.ocr(str(image_path))
            
            texts = _extract_texts(result, min_score)
            return '\n'.join(texts)
            
    except Exception as e:
        print(f"⚠️  处理失败 {image_path}: {e}")
        return ""


def ocr_folder_parallel(frames_dir: str, 
                       min_score: float = 0.3,
                       num_workers: int = None,
                       use_preprocessing: bool = True,
                       hybrid_mode: bool = True) -> str:
    """
    并行处理整个目录的图片（使用线程池）
    
    参数:
        frames_dir: 帧图片目录
        min_score: 最小置信度阈值
        num_workers: 工作线程数（None=自动检测）
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
    
    # 确定工作线程数
    if num_workers is None:
        env_workers = os.environ.get('OCR_WORKERS')
        if env_workers and env_workers.lower() != 'auto':
            try:
                num_workers = int(env_workers)
            except ValueError:
                pass
        
        if num_workers is None:
            # 使用 CPU 核心数的一半
            num_workers = max(1, os.cpu_count() // 2)
    
    print(f"🔧 工作线程: {num_workers}")
    
    # 使用线程池并行处理
    all_results = [None] * len(image_files)
    
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        # 提交所有任务，保持顺序
        futures = {
            executor.submit(
                process_single_image, 
                img, min_score, use_preprocessing, hybrid_mode
            ): i 
            for i, img in enumerate(image_files)
        }
        
        # 使用 tqdm 显示进度
        with tqdm(total=len(image_files), desc="📄 OCR处理", unit="帧", ncols=80) as pbar:
            for future in as_completed(futures):
                idx = futures[future]
                try:
                    all_results[idx] = future.result()
                except Exception as e:
                    print(f"⚠️  任务失败: {e}")
                    all_results[idx] = ""
                pbar.update(1)
    
    # 收集非空文本
    all_texts = [text for text in all_results if text and text.strip()]
    
    # 简单去重（相邻相同的文本）
    unique_texts = []
    prev_text = ""
    for text in all_texts:
        if text != prev_text:
            unique_texts.append(text)
            prev_text = text
    
    return '\n'.join(unique_texts)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        frames_dir = sys.argv[1]
        result = ocr_folder_parallel(
            frames_dir,
            min_score=0.3,
            num_workers=5
        )
        print(f"\n识别结果预览（前200字符）：")
        print(result[:200])
    else:
        print("用法: python ocr_parallel.py <frames_dir>")
        print("示例: python ocr_parallel.py output/test/frames")
