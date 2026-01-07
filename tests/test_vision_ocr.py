#!/usr/bin/env python3
"""
test_vision_ocr.py
测试 Apple Vision OCR 功能

用法:
    python test_vision_ocr.py [图片路径]
"""

import sys
from pathlib import Path

# 添加项目路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def test_vision_ocr():
    """测试 Vision OCR 基本功能"""
    import platform
    
    print("=" * 60)
    print("🧪 Apple Vision OCR 测试")
    print("=" * 60)
    print()
    
    # 1. 检查系统环境
    print("1️⃣  检查系统环境...")
    if platform.system() != 'Darwin':
        print("   ❌ 不是 macOS 系统，Vision OCR 不可用")
        print("   💡 请在 macOS 10.15+ 上运行此测试")
        return False
    
    print(f"   ✅ 系统: {platform.system()} {platform.mac_ver()[0]}")
    print()
    
    # 2. 检查 Swift 可用性
    print("2️⃣  检查 Swift 环境...")
    import subprocess
    try:
        result = subprocess.run(
            ["swift", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            version = result.stdout.strip().split('\n')[0]
            print(f"   ✅ Swift 可用: {version}")
        else:
            print("   ❌ Swift 不可用")
            return False
    except Exception as e:
        print(f"   ❌ Swift 检查失败: {e}")
        return False
    print()
    
    # 3. 检查 Vision OCR 模块
    print("3️⃣  导入 Vision OCR 模块...")
    try:
        from ocr.ocr_vision import init_vision_ocr, ocr_image_vision
        print("   ✅ ocr_vision.py 导入成功")
    except ImportError as e:
        print(f"   ❌ 导入失败: {e}")
        return False
    print()
    
    # 4. 检查 Swift 脚本
    print("4️⃣  检查 Swift OCR 脚本...")
    swift_script = PROJECT_ROOT / "ocr" / "vision_ocr.swift"
    if swift_script.exists():
        print(f"   ✅ 脚本存在: {swift_script}")
    else:
        print(f"   ❌ 脚本不存在: {swift_script}")
        return False
    print()
    
    # 5. 测试图片识别（如果提供了图片路径）
    if len(sys.argv) > 1:
        image_path = Path(sys.argv[1])
        
        print("5️⃣  测试图片识别...")
        print(f"   图片: {image_path}")
        
        if not image_path.exists():
            print(f"   ❌ 图片不存在")
            return False
        
        try:
            print("   初始化 Vision OCR...")
            ocr = init_vision_ocr(lang="ch", recognition_level="accurate")
            
            print("   识别中...")
            text = ocr_image_vision(ocr, str(image_path), debug=True)
            
            print()
            print("   识别结果:")
            print("   " + "-" * 50)
            if text.strip():
                for line in text.split('\n'):
                    print(f"   {line}")
            else:
                print("   （未识别到文本）")
            print("   " + "-" * 50)
            print()
            print("   ✅ 识别完成")
            
        except Exception as e:
            print(f"   ❌ 识别失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    else:
        print("5️⃣  跳过图片识别测试（未提供图片路径）")
        print("   💡 用法: python test_vision_ocr.py <图片路径>")
    
    print()
    print("=" * 60)
    print("✅ Vision OCR 测试完成！")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = test_vision_ocr()
    sys.exit(0 if success else 1)
