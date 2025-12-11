#!/usr/bin/env python3
"""测试不同OCR置信度阈值的识别效果"""

from ocr_utils import init_ocr, ocr_image
from pathlib import Path

print("🔧 初始化OCR...")
ocr = init_ocr(det_model='mobile', rec_model='mobile')

# 测试几张图片
frames_dir = Path("output/test_20251211_184948/frames")
test_frames = sorted(frames_dir.glob("frame_*.png"))[:10]  # 测试前10张

print(f"\n📊 测试 {len(test_frames)} 张图片，对比不同置信度阈值:\n")
print("=" * 80)

# 测试不同的阈值
thresholds = [0.5, 0.3, 0.25, 0.2]

for threshold in thresholds:
    print(f"\n🎯 置信度阈值: {threshold}")
    print("-" * 80)
    
    total_chars = 0
    total_lines = 0
    
    for img in test_frames:
        text = ocr_image(ocr, str(img), min_score=threshold, debug=False)
        char_count = len(text)
        line_count = text.count('\n') + (1 if text else 0)
        total_chars += char_count
        total_lines += line_count
    
    print(f"  识别到: {total_chars} 字符, {total_lines} 行")

print("\n" + "=" * 80)
print("💡 建议: 使用阈值 0.25 可以平衡准确度和召回率")
print("=" * 80)

# 详细展示一张图片的识别结果
print(f"\n📸 详细分析: frame_00010.png")
print("-" * 80)

test_img = frames_dir / "frame_00010.png"
if test_img.exists():
    for threshold in [0.5, 0.3, 0.25]:
        print(f"\n阈值 {threshold}:")
        text = ocr_image(ocr, str(test_img), min_score=threshold, debug=True)
        print(f"识别结果:\n{text}")
        print()
