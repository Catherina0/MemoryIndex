#!/usr/bin/env python3
"""
EasyOCR 测试工具
用于测试和对比 EasyOCR 与 PaddleOCR 的识别效果
"""

import sys
import os
import time
from pathlib import Path


def test_easyocr(image_path, show_details=False):
    """使用 EasyOCR 测试图片"""
    try:
        import easyocr
    except ImportError:
        print("❌ EasyOCR 未安装")
        print("请运行: .venv/bin/pip install easyocr")
        return None
    
    print("🔍 初始化 EasyOCR (中文+英文)...")
    start = time.time()
    reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)
    init_time = time.time() - start
    print(f"   初始化耗时: {init_time:.1f}秒\n")
    
    print(f"📷 识别图片: {image_path}")
    start = time.time()
    results = reader.readtext(
        image_path,
        detail=1,
        paragraph=False,
        text_threshold=0.5,
        low_text=0.3,
        link_threshold=0.3,
        canvas_size=2560,
        mag_ratio=1.5,
    )
    ocr_time = time.time() - start
    print(f"   识别耗时: {ocr_time:.1f}秒\n")
    
    print("=" * 70)
    print(f"📊 识别结果: {len(results)} 个文本区域")
    print("=" * 70)
    
    # 统计
    total_chars = 0
    english_chars = 0
    chinese_chars = 0
    
    for i, (bbox, text, conf) in enumerate(results, 1):
        # 判断语言
        ch_count = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        en_count = sum(1 for c in text if c.isalpha() and ord(c) < 128)
        
        lang_icon = "🀄" if ch_count > en_count else "🔤"
        
        print(f"\n{i}. {lang_icon} [{conf:.3f}] {text}")
        
        if show_details:
            print(f"   中文字符: {ch_count} | 英文字符: {en_count}")
            print(f"   位置: {bbox[0]} -> {bbox[2]}")
        
        total_chars += len(text)
        english_chars += en_count
        chinese_chars += ch_count
    
    print("\n" + "=" * 70)
    print("📈 统计信息:")
    print(f"  检测区域: {len(results)} 个")
    print(f"  总字符数: {total_chars}")
    print(f"  中文字符: {chinese_chars}")
    print(f"  英文字符: {english_chars}")
    print(f"  处理时间: {ocr_time:.1f}秒 (不含初始化)")
    
    return results


def test_paddleocr(image_path, show_details=False):
    """使用 PaddleOCR 测试图片"""
    try:
        from paddleocr import PaddleOCR
    except ImportError:
        print("❌ PaddleOCR 未安装")
        return None
    
    print("🔍 使用 PaddleOCR (中文模式)...")
    start = time.time()
    ocr = PaddleOCR(
        lang='ch',
        use_angle_cls=True,
        det_db_thresh=0.15,
        det_db_box_thresh=0.45,
        det_db_unclip_ratio=2.0,
    )
    init_time = time.time() - start
    print(f"   初始化耗时: {init_time:.1f}秒\n")
    
    print(f"📷 识别图片: {image_path}")
    start = time.time()
    result = ocr.ocr(image_path)
    ocr_time = time.time() - start
    print(f"   识别耗时: {ocr_time:.1f}秒\n")
    
    print("=" * 70)
    
    if result and len(result) > 0:
        item = result[0]
        if isinstance(item, dict):
            texts = item.get('rec_texts', [])
            scores = item.get('rec_scores', [])
            
            print(f"📊 识别结果: {len(texts)} 个文本区域")
            print("=" * 70)
            
            total_chars = 0
            english_chars = 0
            chinese_chars = 0
            
            for i, (text, score) in enumerate(zip(texts, scores), 1):
                ch_count = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
                en_count = sum(1 for c in text if c.isalpha() and ord(c) < 128)
                
                lang_icon = "🀄" if ch_count > en_count else "🔤"
                
                print(f"\n{i}. {lang_icon} [{score:.3f}] {text}")
                
                if show_details:
                    print(f"   中文字符: {ch_count} | 英文字符: {en_count}")
                
                total_chars += len(text)
                english_chars += en_count
                chinese_chars += ch_count
            
            print("\n" + "=" * 70)
            print("📈 统计信息:")
            print(f"  检测区域: {len(texts)} 个")
            print(f"  总字符数: {total_chars}")
            print(f"  中文字符: {chinese_chars}")
            print(f"  英文字符: {english_chars}")
            print(f"  处理时间: {ocr_time:.1f}秒 (不含初始化)")
            
            return list(zip(texts, scores))
    
    print("❌ 未识别到文本")
    return []


def compare_ocr(image_path):
    """对比两种OCR的效果"""
    if not os.path.exists(image_path):
        print(f"❌ 文件不存在: {image_path}")
        return
    
    print("\n" + "🔴" * 35)
    print("对比测试: EasyOCR vs PaddleOCR")
    print("🔴" * 35 + "\n")
    
    print("▶️  测试 1: EasyOCR")
    print("━" * 70)
    easy_results = test_easyocr(image_path, show_details=False)
    
    print("\n\n▶️  测试 2: PaddleOCR")
    print("━" * 70)
    paddle_results = test_paddleocr(image_path, show_details=False)
    
    # 总结对比
    print("\n\n" + "🏁" * 35)
    print("对比总结")
    print("🏁" * 35)
    
    if easy_results and paddle_results:
        print(f"\n检测区域数: EasyOCR {len(easy_results)} vs PaddleOCR {len(paddle_results)}")
        
        # 提取文本进行对比
        easy_texts = set(text for _, text, _ in easy_results)
        paddle_texts = set(text for text, _ in paddle_results)
        
        only_easy = easy_texts - paddle_texts
        only_paddle = paddle_texts - easy_texts
        common = easy_texts & paddle_texts
        
        print(f"\n两者都识别: {len(common)} 条")
        for text in common:
            print(f"  ✓ {text}")
        
        print(f"\n仅 EasyOCR 识别: {len(only_easy)} 条")
        for text in only_easy:
            print(f"  + {text}")
        
        print(f"\n仅 PaddleOCR 识别: {len(only_paddle)} 条")
        for text in only_paddle:
            print(f"  + {text}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='EasyOCR 测试工具')
    parser.add_argument('image', help='图片路径')
    parser.add_argument('--engine', '-e', 
                       choices=['easy', 'paddle', 'compare'],
                       default='compare',
                       help='OCR引擎: easy, paddle, 或 compare (对比)')
    parser.add_argument('--details', '-d', action='store_true',
                       help='显示详细信息')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.image):
        print(f"❌ 文件不存在: {args.image}")
        sys.exit(1)
    
    if args.engine == 'easy':
        test_easyocr(args.image, args.details)
    elif args.engine == 'paddle':
        test_paddleocr(args.image, args.details)
    else:
        compare_ocr(args.image)


if __name__ == "__main__":
    main()
