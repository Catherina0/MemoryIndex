"""
OCR 模块
包含 OCR 识别相关功能
"""

# 尝试导入 PaddleOCR 相关模块（可选）
try:
    from .ocr_utils import init_ocr, ocr_folder_to_text, check_gpu_available
    PADDLE_OCR_AVAILABLE = True
except ImportError:
    PADDLE_OCR_AVAILABLE = False

# 尝试导入 Vision OCR 模块（macOS）
try:
    from .ocr_vision import init_vision_ocr, ocr_image_vision, ocr_folder_vision
    VISION_OCR_AVAILABLE = True
except ImportError:
    VISION_OCR_AVAILABLE = False

# 尝试导入并行 OCR（依赖 PaddleOCR）
try:
    from .ocr_parallel import ocr_folder_parallel
    PARALLEL_OCR_AVAILABLE = True
except ImportError:
    PARALLEL_OCR_AVAILABLE = False

# 导出可用的功能
__all__ = []

if PADDLE_OCR_AVAILABLE:
    __all__.extend(['init_ocr', 'ocr_folder_to_text', 'check_gpu_available'])

if VISION_OCR_AVAILABLE:
    __all__.extend(['init_vision_ocr', 'ocr_image_vision', 'ocr_folder_vision'])

if PARALLEL_OCR_AVAILABLE:
    __all__.append('ocr_folder_parallel')

