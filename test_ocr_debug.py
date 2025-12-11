#!/usr/bin/env python3
"""OCR 调试和测试工具"""

import argparse
import sys
from pathlib import Path
from ocr_utils import init_ocr, ocr_image
import time


def check_api():
    """检查 OCR API 是否正常工作"""
    print("🔍 检查 OCR API 状态...")
    print("-" * 60)
    
    try:
        print("1️⃣  初始化 PaddleOCR...")
        ocr = init_ocr(det_model='mobile', rec_model='mobile')
        print("   ✅ PaddleOCR 初始化成功")
        
        test_frames = list(Path("output").rglob("frames/frame_*.png"))
        if not test_frames:
            print("   ⚠️  未找到测试图片")
            print("   💡 请先运行: make ocr VIDEO=test/test.mp4")
            return False
        
        print(f"\n2️⃣  测试图片识别 ({test_frames[0].name})...")
        result = ocr_image(ocr, str(test_frames[0]), min_score=0.25)
        
        if result:
            print(f"   ✅ 识别成功: {len(result)} 字符")
            print(f"   内容预览: {result[:50]}...")
        else:
            print("   ⚠️  未识别到内容")
        
        print("\n" + "=" * 60)
        print("✅ OCR API 工作正常")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        return False


def test_single_image(image_path, threshold=0.25, debug=False):
    """测试单张图片"""
    print(f"\n📸 测试图片: {image_path}")
    print("-" * 60)
    
    if not Path(image_path).exists():
        print(f"❌ 文件不存在: {image_path}")
        return
    
    print(f"🔧 初始化 OCR (阈值: {threshold})...")
    ocr = init_ocr(det_model='mobile', rec_model='mobile')
    
    print("🔍 开始识别...")
    start_time = time.time()
    text = ocr_image(ocr, image_path, min_score=threshold, debug=debug)
    elapsed = time.time() - start_time
    
    print(f"\n⏱️  耗时: {elapsed:.2f} 秒")
    print(f"📊 结果统计:")
    print(f"   • 字符数: {len(text)}")
    print(f"   • 行数: {text.count(chr(10)) + (1 if text else 0)}")
    
    if text:
        print(f"\n📝 识别内容:")
        print("-" * 60)
        print(text)
        print("-" * 60)
    else:
        print("\n⚠️  未识别到任何内容")


def test_folder(folder_path, samples=10, threshold=0.25):
    """测试文件夹"""
    print(f"\n📂 测试文件夹: {folder_path}")
    print("-" * 60)
    
    folder = Path(folder_path)
    if not folder.exists():
        print(f"❌ 文件夹不存在")
        return
    
    images = sorted(folder.glob("*.png"))[:samples]
    if not images:
        print("❌ 未找到图片")
        return
    
    print(f"🔧 初始化 OCR...")
    ocr = init_ocr(det_model='mobile', rec_model='mobile')
    
    print(f"�� 测试 {len(images)} 张图片\n")
    
    total_chars = 0
    total_time = 0
    
    for i, img in enumerate(images, 1):
        start = time.time()
        text = ocr_image(ocr, str(img), min_score=threshold)
        elapsed = time.time() - start
        
        chars = len(text)
        total_chars += chars
        total_time += elapsed
        
        status = "✓" if chars > 0 else "○"
        print(f"{status} {i:2d}. {img.name}: {chars:4d} 字符 ({elapsed:.1f}s)")
        
        if chars > 0:
            preview = text.replace('\n', ' ')[:40]
            print(f"      {preview}...")
    
    print("\n" + "=" * 60)
    print(f"总字符数: {total_chars}")
    print(f"平均: {total_chars/len(images):.1f} 字符/图")
    print(f"总耗时: {total_time:.1f}s")
    print("=" * 60)


def compare_thresholds(image_path=None):
    """对比不同阈值"""
    print("\n🎯 对比不同置信度阈值")
    print("=" * 60)
    
    if not image_path:
        test_frames = list(Path("output").rglob("frames/frame_*.png"))
        if not test_frames:
            print("❌ 未找到测试图片")
            return
        image_path = str(test_frames[5])
    
    print(f"📸 测试图片: {Path(image_path).name}\n")
    
    ocr = init_ocr(det_model='mobile', rec_model='mobile')
    thresholds = [0.5, 0.4, 0.3, 0.25, 0.2, 0.15]
    
    print("阈值  │ 字符数 │ 内容预览")
    print("─────┼────────┼" + "─" * 40)
    
    for thresh in thresholds:
        text = ocr_image(ocr, image_path, min_score=thresh)
        chars = len(text)
        preview = text.replace('\n', ' ')[:35] if text else "(无)"
        print(f"{thresh:.2f} │ {chars:6d} │ {preview}...")


def show_help():
    """显示帮助"""
    print("""
OCR 调试工具使用指南
════════════════════════════════════════

📋 功能:
  --check-api           检查 OCR 是否正常
  --image <path>        测试单张图片
  --folder <path>       测试整个文件夹
  --compare-thresholds  对比不同阈值
  --threshold <value>   指定阈值(默认0.25)
  --samples <num>       测试图片数量(默认10)
  --debug               显示详细信息

📚 示例:
  python test_ocr_debug.py --check-api
  python test_ocr_debug.py --image test.png --debug
  python test_ocr_debug.py --folder output/xxx/frames --samples 20
  python test_ocr_debug.py --compare-thresholds

💡 详细文档: docs/OCR_DEBUG_GUIDE.md
""")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--check-api', action='store_true')
    parser.add_argument('--image', type=str)
    parser.add_argument('--folder', type=str)
    parser.add_argument('--compare-thresholds', action='store_true')
    parser.add_argument('--threshold', type=float, default=0.25)
    parser.add_argument('--samples', type=int, default=10)
    parser.add_argument('--debug', action='store_true')
    parser.add_argument('--help', '-h', action='store_true')
    
    args = parser.parse_args()
    
    if args.help or len(sys.argv) == 1:
        show_help()
    elif args.check_api:
        check_api()
    elif args.image:
        test_single_image(args.image, args.threshold, args.debug)
    elif args.folder:
        test_folder(args.folder, args.samples, args.threshold)
    elif args.compare_thresholds:
        compare_thresholds(args.image)
