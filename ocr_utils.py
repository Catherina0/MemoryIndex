# ocr_utils.py
import os
import tempfile
from paddleocr import PaddleOCR
from PIL import Image, ImageEnhance
from tqdm import tqdm


def preprocess_image(image_path, enhance_contrast=True, roi_bottom_only=False, bottom_ratio=0.25):
    """
    图像预处理：提高复杂背景下的 OCR 识别率
    
    参数:
        image_path: 图片路径
        enhance_contrast: 是否增强对比度和锐化
        roi_bottom_only: 是否只处理底部字幕区域
        bottom_ratio: 底部区域占比 (0.25 = 底部 25%)
    
    策略:
        - ROI 裁剪：只处理字幕区域，去除复杂背景
        - 对比度增强：让文字与背景对比更明显
        - 轻微锐化：边界更清晰，利于小字识别
    """
    img = Image.open(image_path)
    
    # ROI 裁剪：如果主要是底部字幕，只截取底部区域
    if roi_bottom_only:
        width, height = img.size
        top = int(height * (1 - bottom_ratio))
        img = img.crop((0, top, width, height))
    
    # 对比度增强：让文字与背景对比更明显
    if enhance_contrast:
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.5)  # 适度增强，不要过度
        
        # 轻微锐化：边界更清晰
        sharpener = ImageEnhance.Sharpness(img)
        img = sharpener.enhance(1.3)
    
    return img


def init_ocr(lang="ch", use_gpu=False, det_model="server", rec_model="server"):
    """
    初始化 OCR 模型 - 升级到 PP-OCRv4 server 版本
    
    参数:
        lang: 语言，'ch'(中文+英文混合)，不要用纯英文模型
        use_gpu: 是否使用 GPU，默认 False
        det_model: 检测模型 - 'server'(精度优先，复杂背景强)/'mobile'(速度优先)
        rec_model: 识别模型 - 'server'(精度优先)/'mobile'(速度优先)
    
    模型选择策略:
        - 本地开发/高性能: server + server (效果最好)
        - 小服务器/资源有限: mobile + server (平衡)
        - 极低资源: mobile + mobile (速度优先)
    
    参数策略 (核心思路):
        1. 检测阶段：放宽阈值，多抓候选框 ("宁可多，不可漏")
        2. 识别阶段：提高置信度要求，严格筛选 ("宁缺毋滥")
        3. 方向分类：必须开启，应对旋转/倾斜文本
        4. 分辨率提升：识别输入放大，利于小字幕
    """
    # PP-OCRv4 server 模型 + 优化参数配置
    ocr = PaddleOCR(
        lang=lang,  # 'ch' 模型支持中英文混合，不要用纯英文
        
        # 【必须开启】方向分类：处理旋转、倾斜、竖排文本
        use_angle_cls=True,
        
        # 【检测阶段：宽松策略】多抓候选框
        det_db_thresh=0.2,          # 检测二值化阈值 (0.2 = 较宽松)
        det_db_box_thresh=0.4,      # 检测框置信度 (降低以保留更多候选)
        det_db_unclip_ratio=2.2,    # 文本框扩展比例 (稍大，避免截断)
        
        # 【识别阶段：严格策略】提高输入质量
        rec_batch_num=6,            # 批处理大小
        # rec_image_shape 在新版中已不适用，由模型自动处理
    )
    return ocr


def ocr_image(ocr, image_path: str, min_score: float = 0.3, debug: bool = False, 
              use_preprocessing: bool = True, roi_bottom_only: bool = False,
              hybrid_mode: bool = True) -> str:
    """
    对单张图片做 OCR，返回识别到的文本（按行拼接）。
    支持 PaddleOCR 3.x 新版 API 格式 + 图像预处理 + 混合识别模式。
    
    参数:
        ocr: PaddleOCR 实例
        image_path: 图片路径
        min_score: 最小置信度阈值（识别阶段严格过滤，默认 0.3）
        debug: 是否显示调试信息
        use_preprocessing: 是否使用图像预处理（对比度增强+锐化）
        roi_bottom_only: 是否只处理底部字幕区域（仅在 hybrid_mode=False 时生效）
        hybrid_mode: 混合模式（同时识别字幕区和全画面，推荐开启）
    
    混合模式策略（hybrid_mode=True）:
        1. 第一次OCR：处理底部25%字幕区（预处理+ROI）→ 高准确度字幕
        2. 第二次OCR：处理整个画面（预处理，无ROI）→ 捕获其他文字
        3. 合并去重：避免字幕区被重复识别
    
    单一模式策略（hybrid_mode=False）:
        - 根据 roi_bottom_only 决定处理区域
        - 检测阶段已经放宽（在 init_ocr 中配置）
        - 识别阶段严格筛选（通过 min_score 过滤低质量结果）
    """
    try:
        all_texts = set()  # 使用集合去重
        
        # 【混合模式】同时识别字幕区和全画面
        if hybrid_mode:
            # 第一次OCR：底部字幕区（预处理 + ROI）
            if debug:
                print(f"    [混合模式] 第一次OCR: 底部字幕区（25%）")
            
            processed_subtitle = preprocess_image(
                image_path,
                enhance_contrast=True,
                roi_bottom_only=True,  # 只处理底部25%
                bottom_ratio=0.25
            )
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                processed_subtitle.save(tmp.name)
                temp_path_subtitle = tmp.name
            
            try:
                result_subtitle = ocr.ocr(temp_path_subtitle)
                texts_subtitle = _extract_texts_from_result(result_subtitle, min_score, debug, "字幕区")
                all_texts.update(texts_subtitle)
            finally:
                os.unlink(temp_path_subtitle)
            
            # 第二次OCR：全画面（预处理，无ROI）
            if debug:
                print(f"    [混合模式] 第二次OCR: 全画面")
            
            if use_preprocessing:
                processed_full = preprocess_image(
                    image_path,
                    enhance_contrast=True,
                    roi_bottom_only=False,  # 处理整个画面
                    bottom_ratio=0.25
                )
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    processed_full.save(tmp.name)
                    temp_path_full = tmp.name
                
                try:
                    result_full = ocr.ocr(temp_path_full)
                    texts_full = _extract_texts_from_result(result_full, min_score, debug, "全画面")
                    all_texts.update(texts_full)
                finally:
                    os.unlink(temp_path_full)
            else:
                result_full = ocr.ocr(image_path)
                texts_full = _extract_texts_from_result(result_full, min_score, debug, "全画面")
                all_texts.update(texts_full)
            
            # 返回合并去重后的结果
            return '\n'.join(sorted(all_texts)) if all_texts else ""
        
        # 【单一模式】只进行一次OCR
        else:
            # 图像预处理：提高复杂背景下的识别率
            if use_preprocessing:
                processed_img = preprocess_image(
                    image_path,
                    enhance_contrast=True,
                    roi_bottom_only=roi_bottom_only,
                    bottom_ratio=0.25  # 只处理底部 25% 区域（字幕区）
                )
                # 保存到临时文件（PaddleOCR 需要文件路径）
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    processed_img.save(tmp.name)
                    temp_path = tmp.name
                
                try:
                    result = ocr.ocr(temp_path)
                finally:
                    os.unlink(temp_path)  # 清理临时文件
            else:
                result = ocr.ocr(image_path)
        
        lines = []
        filtered_count = 0
        
        if result and len(result) > 0:
            item = result[0]
            
            # 新版 API 返回字典格式，包含 rec_texts 和 rec_scores
            if isinstance(item, dict):
                rec_texts = item.get('rec_texts', [])
                rec_scores = item.get('rec_scores', [])
                
                for text, score in zip(rec_texts, rec_scores):
                    if score >= min_score:  # 过滤低置信度结果
                        lines.append(text)
                    else:
                        filtered_count += 1
                        if debug:
                            print(f"    [过滤] {text} (置信度: {score:.2f})")
            
            # 兼容旧版 API（列表格式）
            elif isinstance(item, list):
                for line in item:
                    try:
                        if len(line) >= 2 and line[1]:
                            text_info = line[1]
                            if isinstance(text_info, (list, tuple)) and len(text_info) >= 2:
                                text = text_info[0]
                                score = text_info[1]
                                if score >= min_score:
                                    lines.append(text)
                                else:
                                    filtered_count += 1
                                    if debug:
                                        print(f"    [过滤] {text} (置信度: {score:.2f})")
                    except (IndexError, TypeError):
                        continue
        
        if debug and filtered_count > 0:
            print(f"    ℹ️  {image_path}: 识别 {len(lines)} 行，过滤 {filtered_count} 行")
        
        return "\n".join(lines)
    except Exception as e:
        print(f"  ⚠️  OCR 图片失败 {image_path}: {e}")
        return ""


def ocr_folder_to_text(ocr, frames_dir: str, min_score: float = 0.3, debug: bool = False,
                       use_preprocessing: bool = True, roi_bottom_only: bool = True,
                       hybrid_mode: bool = True) -> str:
    """
    对整个目录下的所有图片做 OCR，按文件名顺序拼接成一个大文本。
    带进度条显示处理进度 + 多帧冗余去重 + 混合识别模式。
    
    参数:
        ocr: PaddleOCR 实例
        frames_dir: 帧图片目录
        min_score: 最小置信度阈值（识别阶段严格，默认 0.3）
        debug: 是否显示调试信息
        use_preprocessing: 是否使用图像预处理
        roi_bottom_only: 是否只处理底部字幕区（仅在 hybrid_mode=False 时生效）
        hybrid_mode: 混合模式，同时识别字幕和画面其他文字（推荐开启）
    
    混合模式说明（hybrid_mode=True）:
        - 每一帧进行两次OCR：底部字幕区 + 全画面
        - 自动合并去重，避免重复识别
        - 既能高准确度识别字幕，又能捕获画面中的其他文字
    
    多帧冗余策略:
        - 同一行字幕会在连续多帧出现
        - 相似度 > 80% 的连续帧会被去重
        - 只保留最好的识别结果
    """
    files = sorted(
        f for f in os.listdir(frames_dir)
        if f.lower().endswith((".png", ".jpg", ".jpeg"))
    )

    if not files:
        print("  ⚠️  未找到图片文件")
        return ""
    
    print(f"  📊 找到 {len(files)} 个帧图片，开始OCR识别...")
    print(f"  🎯 识别策略: 检测宽松 + 识别严格 (min_score={min_score})")
    
    if hybrid_mode:
        print(f"  🔄 混合模式: 同时识别【字幕区】+【全画面】(推荐)")
    else:
        mode_desc = '开启 (对比度+锐化' + ('+ROI裁剪)' if roi_bottom_only else ')') if use_preprocessing else '关闭'
        print(f"  🖼️  预处理: {mode_desc}")
    
    all_text_parts = []
    prev_text = ""  # 用于多帧冗余去重
    duplicate_count = 0
    
    # 使用tqdm显示进度条
    desc = "  🔍 OCR进度 (混合)" if hybrid_mode else "  🔍 OCR进度 (Server)"
    for fname in tqdm(files, desc=desc, unit="帧", ncols=80):
        path = os.path.join(frames_dir, fname)
        text = ocr_image(ocr, path, min_score=min_score, debug=debug,
                        use_preprocessing=use_preprocessing, 
                        roi_bottom_only=roi_bottom_only,
                        hybrid_mode=hybrid_mode)
        
        if text.strip():
            # 多帧冗余去重：如果与上一帧相似度很高，跳过
            if prev_text:
                # 简单相似度计算：相同字符数 / 最大长度
                common = sum(1 for a, b in zip(text, prev_text) if a == b)
                similarity = common / max(len(text), len(prev_text), 1)
                
                if similarity >= 0.8:  # 80% 以上相似，认为是重复帧
                    duplicate_count += 1
                    continue
            
            all_text_parts.append(f"=== Frame: {fname} ===\n{text}\n")
            prev_text = text
    
    if duplicate_count > 0:
        print(f"  ✂️  去重: 过滤了 {duplicate_count} 个重复帧 (相似度 ≥ 80%)")

    return "\n".join(all_text_parts)


def _extract_texts_from_result(result, min_score: float, debug: bool = False, source: str = "") -> list:
    """
    从OCR结果中提取文本（辅助函数）
    
    参数:
        result: PaddleOCR 识别结果
        min_score: 最小置信度阈值
        debug: 是否显示调试信息
        source: 来源标识（用于调试）
    
    返回:
        list: 识别出的文本列表
    """
    texts = []
    
    if not result or len(result) == 0:
        return texts
    
    item = result[0]
    
    # 新版 API 返回字典格式
    if isinstance(item, dict):
        rec_texts = item.get('rec_texts', [])
        rec_scores = item.get('rec_scores', [])
        
        for text, score in zip(rec_texts, rec_scores):
            if score >= min_score:
                texts.append(text)
                if debug and source:
                    print(f"      [{source}] [{score:.2f}] {text}")
    
    # 兼容旧版 API（列表格式）
    elif isinstance(item, list):
        for line in item:
            try:
                if len(line) >= 2 and line[1]:
                    text_info = line[1]
                    if isinstance(text_info, (list, tuple)) and len(text_info) >= 2:
                        text = text_info[0]
                        score = text_info[1]
                        if score >= min_score:
                            texts.append(text)
                            if debug and source:
                                print(f"      [{source}] [{score:.2f}] {text}")
            except (IndexError, TypeError):
                continue
    
    return texts
