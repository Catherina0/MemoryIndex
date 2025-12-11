#!/usr/bin/env python3
"""
专门测试英文文本识别的脚本
针对地铁场景中的英文标识、字幕等
"""

from ocr_utils import init_ocr, ocr_image
from pathlib import Path
import time

def test_aggressive_params():
    """使用更激进的参数测试英文识别"""
    
    print("🔧 测试更激进的OCR参数以识别英文文本")
    print("=" * 70)
    
    # 找到最近的测试图片
    test_frames = sorted(Path("output").rglob("frames/frame_*.png"))
    if not test_frames:
        print("❌ 未找到测试图片")
        return
    
    # 选择几张有代表性的图片
    test_images = [test_frames[4], test_frames[5], test_frames[7], test_frames[10]]
    
    # 不同的参数配置
    configs = [
        {
            "name": "当前配置 (优化后)",
            "params": {"min_score": 0.25},
            "note": "det_db_thresh=0.2, unclip=1.8"
        },
        {
            "name": "激进配置 A",
            "params": {"min_score": 0.2},
            "note": "降低置信度到0.2"
        },
        {
            "name": "激进配置 B", 
            "params": {"min_score": 0.15},
            "note": "极低置信度0.15"
        },
    ]
    
    print("\n📊 测试不同配置对英文识别的影响:\n")
    
    # 初始化OCR
    ocr = init_ocr(det_model='mobile', rec_model='mobile')
    
    for config in configs:
        print(f"\n🎯 配置: {config['name']}")
        print(f"   参数: {config['note']}")
        print("-" * 70)
        
        total_chars = 0
        english_chars = 0
        
        for img in test_images[:2]:  # 只测试前2张，加快速度
            text = ocr_image(ocr, str(img), min_score=config['params']['min_score'])
            chars = len(text)
            # 粗略估计英文字符数
            eng = sum(1 for c in text if c.isalpha() and ord(c) < 128)
            
            total_chars += chars
            english_chars += eng
            
            if chars > 0:
                preview = text.replace('\n', ' ')[:50]
                print(f"  {img.name}: {chars}字符 ({eng}英文) - {preview}...")
        
        print(f"\n  📈 统计: 总字符={total_chars}, 英文字符≈{english_chars}")
        print()


def test_with_server_model():
    """测试使用server模型是否能提升英文识别"""
    
    print("\n" + "=" * 70)
    print("🚀 测试 SERVER 模型（更高精度）")
    print("=" * 70)
    print("⚠️  注意: server模型处理较慢，请耐心等待...\n")
    
    test_frames = sorted(Path("output").rglob("frames/frame_*.png"))
    if not test_frames:
        return
    
    # 只测试1张图片
    test_img = test_frames[5]  # OLD STREET 那张
    
    print(f"📸 测试图片: {test_img.name}")
    print("   场景: 地铁站标识 (OLD STREET)")
    print()
    
    # Mobile模型
    print("1️⃣  Mobile 模型:")
    ocr_mobile = init_ocr(det_model='mobile', rec_model='mobile')
    start = time.time()
    text_mobile = ocr_image(ocr_mobile, str(test_img), min_score=0.2)
    time_mobile = time.time() - start
    
    eng_mobile = sum(1 for c in text_mobile if c.isalpha() and ord(c) < 128)
    print(f"   字符: {len(text_mobile)}, 英文: {eng_mobile}, 耗时: {time_mobile:.1f}s")
    print(f"   内容: {text_mobile.replace(chr(10), ' ')[:80]}...")
    
    print()
    print("   提示: 如果英文识别不理想，考虑:")
    print("   • 进一步降低 det_db_thresh (在 ocr_utils.py)")
    print("   • 增大 det_db_unclip_ratio 到 2.0 或 2.2")
    print("   • 使用 server 模型: make ocr VIDEO=xxx DET_MODEL=server REC_MODEL=server")


def show_detailed_analysis():
    """显示详细的识别分析"""
    
    print("\n" + "=" * 70)
    print("🔍 详细分析建议")
    print("=" * 70)
    
    print("""
针对英文文本识别不全的问题，建议采取以下措施:

1️⃣  降低检测阈值 (在 ocr_utils.py 中修改 init_ocr 函数):
   
   det_db_thresh=0.15,        # 从 0.2 降低到 0.15
   det_db_box_thresh=0.45,    # 从 0.5 降低到 0.45
   det_db_unclip_ratio=2.0,   # 从 1.8 增大到 2.0

2️⃣  降低置信度过滤 (在 process_video.py 中):
   
   ocr_text = ocr_folder_to_text(ocr, str(frames_dir), min_score=0.2)
   # 或更低: min_score=0.15

3️⃣  使用更精确的模型:
   
   make ocr VIDEO=xxx.mp4 DET_MODEL=server REC_MODEL=server

4️⃣  针对地铁场景的特殊优化:
   • 地铁标识通常是大号英文，应该更容易识别
   • 如果还识别不到，可能是图片分辨率或光照问题
   • 可以尝试提高视频抽帧的质量

💡 立即测试优化效果:

   # 修改 ocr_utils.py 后运行:
   python test_english_text.py

   # 或直接测试单张图片:
   python test_ocr_debug.py --image output/xxx/frames/frame_00005.png --debug --threshold 0.15
""")


if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════╗
║          英文文本识别测试工具                                ║
╚══════════════════════════════════════════════════════════════╝
""")
    
    test_aggressive_params()
    test_with_server_model()
    show_detailed_analysis()
    
    print("\n" + "=" * 70)
    print("✅ 测试完成")
    print("=" * 70)
