"""
OCR 模块
包含 OCR 识别相关功能
"""

from .ocr_utils import init_ocr, ocr_folder_to_text, check_gpu_available
from .ocr_parallel import ocr_folder_parallel

__all__ = [
    'init_ocr',
    'ocr_folder_to_text',
    'check_gpu_available',
    'ocr_folder_parallel',
]
