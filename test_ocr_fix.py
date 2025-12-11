#!/usr/bin/env python3
"""快速测试OCR修复是否有效"""

from ocr_utils import init_ocr, ocr_image
from pathlib import Path

print("🔧 初始化OCR...")
ocr = init_ocr(det_model='mobile', rec_model='mobile')

# 测试几张图片
frames_dir = Path("output/test_20251211_184948/frames")
test_frames = sorted(frames_dir.glob("frame_*.png"))[:5]  # 只测试前5张

print(f"\n📊 测试 {len(test_frames)} 张图片:\n")

total_chars = 0
results = []

for img in test_frames:
    text = ocr_image(ocr, str(img))
    char_count = len(text)
    total_chars += char_count
    results.append((img.name, text, char_count))
    print(f"✓ {img.name}: {char_count} 字符")
    if text:
        # 只显示前50个字符
        preview = text.replace('\n', ' ')[:50]
        print(f"  内容: {preview}{'...' if len(text) > 50 else ''}")
    print()

print("=" * 60)
print(f"✅ 总计识别: {total_chars} 字符")
print(f"✅ OCR功能: {'正常 ✓' if total_chars > 0 else '异常 ✗'}")
print("=" * 60)
