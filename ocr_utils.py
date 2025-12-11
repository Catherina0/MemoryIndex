# ocr_utils.py
import os
from paddleocr import PaddleOCR
from tqdm import tqdm


def init_ocr(lang="ch", use_gpu=False, det_model="server", rec_model="server"):
    """
    初始化 OCR 模型。
    
    参数:
        lang: 语言，'ch'(中文)/'en'(英文)/'chinese_cht'(繁体) 等
        use_gpu: 是否使用 GPU，默认 False
        det_model: 检测模型类型 - 'server'(精度高)/mobile'(速度快)
        rec_model: 识别模型类型 - 'server'(精度高)/'mobile'(速度快)
    
    模型选择建议:
        - 高性能设备: det_model='server', rec_model='server'
        - 普通设备: det_model='mobile', rec_model='mobile'
        - 平衡模式: det_model='mobile', rec_model='server'
    """
    # 根据模型类型设置版本
    det_model_dir = None
    rec_model_dir = None
    
    # 简化版本：直接使用 PaddleOCR 的默认参数
    # 新版 PaddleOCR 会自动根据环境选择合适的模型和设备
    # mobile/server 主要通过模型大小区分，不需要显式指定路径
    
    # 注意：新版 PaddleOCR 不再支持 use_gpu 参数
    # GPU 加速由 PaddlePaddle 自动检测和使用
    
    ocr = PaddleOCR(
        lang=lang,
        use_angle_cls=True
    )
    return ocr


def ocr_image(ocr, image_path: str) -> str:
    """
    对单张图片做 OCR，返回识别到的文本（按行拼接）。
    """
    try:
        result = ocr.ocr(image_path)
        lines = []
        if result and result[0]:  # 确保有结果
            for line in result[0]:  # 新版 API 返回格式
                try:
                    # line 格式: [box, (text, score)]
                    if len(line) >= 2 and line[1]:
                        text_info = line[1]
                        if isinstance(text_info, (list, tuple)) and len(text_info) >= 2:
                            text = text_info[0]  # 文本
                            score = text_info[1]  # 置信度
                            if score >= 0.5:  # 过滤特别不靠谱的
                                lines.append(text)
                except (IndexError, TypeError) as e:
                    # 跳过格式异常的行
                    continue
        return "\n".join(lines)
    except Exception as e:
        print(f"  ⚠️  OCR 图片失败 {image_path}: {e}")
        return ""


def ocr_folder_to_text(ocr, frames_dir: str) -> str:
    """
    对整个目录下的所有图片做 OCR，按文件名顺序拼接成一个大文本。
    带进度条显示处理进度。
    """
    files = sorted(
        f for f in os.listdir(frames_dir)
        if f.lower().endswith((".png", ".jpg", ".jpeg"))
    )

    if not files:
        print("  ⚠️  未找到图片文件")
        return ""
    
    print(f"  📊 找到 {len(files)} 个帧图片，开始OCR识别...")
    
    all_text_parts = []
    # 使用tqdm显示进度条
    for fname in tqdm(files, desc="  🔍 OCR进度", unit="帧", ncols=80):
        path = os.path.join(frames_dir, fname)
        text = ocr_image(ocr, path)
        if text.strip():
            all_text_parts.append(f"=== Frame: {fname} ===\n{text}\n")

    return "\n".join(all_text_parts)
