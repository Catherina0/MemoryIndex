#!/usr/bin/env python3
"""
双语言OCR工具 - 同时使用中英文模型
解决英文文本检测不全的问题
"""

from paddleocr import PaddleOCR
from PIL import Image, ImageEnhance
import os
import sys


def enhance_image(image_path, output_path=None):
    """
    图像增强预处理
    提高对比度和锐度，便于文字检测
    """
    img = Image.open(image_path)
    
    # 提高对比度
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.8)
    
    # 锐化
    sharpener = ImageEnhance.Sharpness(img)
    img = sharpener.enhance(1.5)
    
    if output_path:
        img.save(output_path)
    
    return img


def ocr_bilingual(image_path, enhance=True, debug=False):
    """
    使用中英文两个OCR模型进行识别
    
    Args:
        image_path: 图片路径
        enhance: 是否进行图像增强
        debug: 是否输出调试信息
    
    Returns:
        dict: {
            'chinese': [(text, score), ...],
            'english': [(text, score), ...],
            'all_texts': [text, text, ...]
        }
    """
    # 图像增强
    if enhance:
        if debug:
            print("📸 应用图像增强...")
        temp_path = image_path + ".enhanced.png"
        enhance_image(image_path, temp_path)
        process_path = temp_path
    else:
        process_path = image_path
    
    results = {
        'chinese': [],
        'english': [],
        'all_texts': []
    }
    
    # 1. 中文OCR - 识别中文字幕
    if debug:
        print("\n🀄 运行中文OCR...")
    
    ocr_ch = PaddleOCR(
        lang='ch',
        use_angle_cls=True,
        det_db_thresh=0.15,  # 中文使用标准参数
        det_db_box_thresh=0.45,
        det_db_unclip_ratio=2.0,
    )
    
    result_ch = ocr_ch.ocr(process_path)
    if result_ch and len(result_ch) > 0:
        item = result_ch[0]
        if isinstance(item, dict):
            texts = item.get('rec_texts', [])
            scores = item.get('rec_scores', [])
            for text, score in zip(texts, scores):
                if score >= 0.15:  # 最小置信度
                    results['chinese'].append((text, score))
                    results['all_texts'].append(text)
                    if debug:
                        print(f"  ✓ [{score:.3f}] {text}")
    
    # 2. 英文OCR - 识别英文标识
    if debug:
        print("\n🔤 运行英文OCR...")
    
    ocr_en = PaddleOCR(
        lang='en',
        use_angle_cls=True,
        det_db_thresh=0.1,  # 英文使用更低阈值
        det_db_box_thresh=0.3,
        det_db_unclip_ratio=3.0,  # 更大的扩展比例
    )
    
    result_en = ocr_en.ocr(process_path)
    if result_en and len(result_en) > 0:
        item = result_en[0]
        if isinstance(item, dict):
            texts = item.get('rec_texts', [])
            scores = item.get('rec_scores', [])
            for text, score in zip(texts, scores):
                if score >= 0.1:  # 英文使用更低的最小置信度
                    # 过滤掉与中文重复的内容
                    if text not in results['all_texts']:
                        results['english'].append((text, score))
                        results['all_texts'].append(text)
                        if debug:
                            print(f"  ✓ [{score:.3f}] {text}")
    
    # 清理临时文件
    if enhance and os.path.exists(temp_path):
        os.remove(temp_path)
    
    return results


def main():
    """命令行工具"""
    import argparse
    
    parser = argparse.ArgumentParser(description='双语言OCR - 同时识别中英文')
    parser.add_argument('image', help='图片路径')
    parser.add_argument('--no-enhance', action='store_true', help='不进行图像增强')
    parser.add_argument('--debug', action='store_true', help='显示调试信息')
    parser.add_argument('--output', '-o', help='输出文件路径（可选）')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.image):
        print(f"❌ 文件不存在: {args.image}")
        sys.exit(1)
    
    print(f"🔍 处理图片: {args.image}")
    print("=" * 70)
    
    # 运行双语言OCR
    results = ocr_bilingual(
        args.image,
        enhance=not args.no_enhance,
        debug=args.debug
    )
    
    # 输出结果
    print("\n" + "=" * 70)
    print("📊 识别结果:")
    print("=" * 70)
    
    print(f"\n🀄 中文文本 ({len(results['chinese'])} 条):")
    for text, score in results['chinese']:
        print(f"  [{score:.3f}] {text}")
    
    print(f"\n🔤 英文文本 ({len(results['english'])} 条):")
    for text, score in results['english']:
        print(f"  [{score:.3f}] {text}")
    
    print(f"\n📝 总计: {len(results['all_texts'])} 条文本")
    
    # 保存到文件
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write("=== 中文文本 ===\n")
            for text, score in results['chinese']:
                f.write(f"[{score:.3f}] {text}\n")
            f.write("\n=== 英文文本 ===\n")
            for text, score in results['english']:
                f.write(f"[{score:.3f}] {text}\n")
            f.write(f"\n=== 所有文本 ===\n")
            for text in results['all_texts']:
                f.write(f"{text}\n")
        print(f"\n✅ 结果已保存到: {args.output}")


if __name__ == "__main__":
    main()
