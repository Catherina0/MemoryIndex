#!/usr/bin/env python3
"""
示例脚本：演示项目的各个模块

这个脚本展示了如何直接调用 ocr_utils 和 process_video 中的函数
"""

import sys
from pathlib import Path

# ========== 测试 1: OCR 工具导入 ==========
def test_ocr_import():
    """验证 OCR 模块可以正确导入"""
    print("📝 测试 1: OCR 模块导入...")
    try:
        from ocr_utils import init_ocr, ocr_image, ocr_folder_to_text
        print("  ✓ OCR 模块导入成功")
        return True
    except ImportError as e:
        print(f"  ✗ 导入失败: {e}")
        return False


# ========== 测试 2: 视频处理模块导入 ==========
def test_process_video_import():
    """验证视频处理模块可以正确导入"""
    print("📽️  测试 2: 视频处理模块导入...")
    try:
        from process_video import (
            extract_audio,
            extract_frames,
            process_video,
            transcribe_audio_with_groq,
            summarize_with_gpt_oss_120b,
        )
        print("  ✓ 视频处理模块导入成功")
        return True
    except ImportError as e:
        print(f"  ✗ 导入失败: {e}")
        return False


# ========== 测试 3: ffmpeg 可用性 ==========
def test_ffmpeg_available():
    """检查 ffmpeg 是否可用"""
    print("🎬 测试 3: ffmpeg 可用性...")
    import subprocess
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            print(f"  ✓ ffmpeg 可用: {version_line}")
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"  ✗ ffmpeg 不可用或超时: {e}")
        return False


# ========== 测试 4: 虚拟环境 ==========
def test_virtual_env():
    """检查是否在虚拟环境中运行"""
    print("🐍 测试 4: 虚拟环境检查...")
    in_venv = sys.prefix != sys.base_prefix
    if in_venv:
        print(f"  ✓ 在虚拟环境中运行: {sys.prefix}")
        return True
    else:
        print(f"  ⚠️  未在虚拟环境中运行")
        return False


# ========== 测试 5: 依赖完整性 ==========
def test_dependencies():
    """检查所有必需的 Python 依赖"""
    print("📦 测试 5: Python 依赖检查...")
    required = ['cv2', 'paddleocr', 'numpy']
    missing = []
    for lib in required:
        try:
            __import__(lib)
            print(f"  ✓ {lib} OK")
        except ImportError:
            print(f"  ✗ {lib} 缺失")
            missing.append(lib)
    
    if missing:
        print(f"\n  缺失的依赖: {', '.join(missing)}")
        print(f"  请运行: pip install -r requirements.txt")
        return False
    return True


# ========== 测试 6: 输出目录结构 ==========
def test_output_structure():
    """检查输出目录结构"""
    print("📁 测试 6: 输出目录结构...")
    output_dir = Path("output")
    
    if output_dir.exists():
        print(f"  ✓ output 目录已存在")
        subdirs = [d.name for d in output_dir.iterdir() if d.is_dir()]
        for subdir in sorted(subdirs):
            print(f"    - {subdir}/")
        return True
    else:
        print(f"  ℹ️  output 目录不存在（首次运行时会创建）")
        return True


# ========== 测试 7: Groq API 配置 ==========
def test_groq_config():
    """检查 Groq API 配置"""
    print("🤖 测试 7: Groq API 配置...")
    try:
        import os
        from dotenv import load_dotenv
        
        load_dotenv()
        api_key = os.getenv('GROQ_API_KEY')
        
        if api_key and api_key != "":
            # 不显示完整 key，只显示前后几位
            masked_key = f"{api_key[:7]}...{api_key[-4:]}" if len(api_key) > 11 else "***"
            print(f"  ✓ Groq API Key 已配置: {masked_key}")
            
            # 尝试初始化客户端
            try:
                from groq import Groq
                client = Groq(api_key=api_key)
                print(f"  ✓ Groq 客户端初始化成功")
                return True
            except Exception as e:
                print(f"  ⚠️  Groq 客户端初始化失败: {e}")
                return False
        else:
            print(f"  ℹ️  Groq API Key 未配置（可选）")
            print(f"     若需使用 Groq 功能，请编辑 .env 文件")
            return True  # 不强制要求
    except Exception as e:
        print(f"  ⚠️  检查失败: {e}")
        return True  # 不强制要求


# ========== 主测试流程 ==========
def main():
    print("=" * 60)
    print("🚀 Video Report Pipeline - 环境检查")
    print("=" * 60)
    print()

    tests = [
        test_virtual_env,
        test_ffmpeg_available,
        test_dependencies,
        test_ocr_import,
        test_process_video_import,
        test_output_structure,
        test_groq_config,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"  ✗ 测试出错: {e}")
            results.append(False)
        print()

    # 总结
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"✅ 测试完成: {passed}/{total} 通过")
    print("=" * 60)

    if passed == total:
        print("\n🎉 环境准备完毕！你可以开始运行:")
        print("  python process_video.py /path/to/video.mp4")
        print("  python process_video.py /path/to/video.mp4 --with-frames")
        return 0
    else:
        print("\n⚠️  请解决上述问题后再运行")
        return 1


if __name__ == "__main__":
    sys.exit(main())
