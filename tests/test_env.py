#!/usr/bin/env python3
"""
环境测试脚本 - 快速验证基本依赖是否安装正确
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def test_core_imports():
    """测试核心模块导入"""
    print("🧪 测试核心模块...")
    
    errors = []
    
    # 必需模块
    required = [
        ('groq', 'Groq API 客户端'),
        ('paddleocr', 'PaddleOCR'),
        ('cv2', 'OpenCV'),
        ('numpy', 'NumPy'),
        ('dotenv', 'python-dotenv'),
        ('tabulate', 'Tabulate'),
    ]
    
    for module, name in required:
        try:
            __import__(module)
            print(f"   ✅ {name}")
        except ImportError as e:
            print(f"   ❌ {name}: {e}")
            errors.append(module)
    
    # 可选模块
    optional = [
        ('whoosh', 'Whoosh (中文搜索)'),
        ('jieba', 'jieba (中文分词)'),
    ]
    
    for module, name in optional:
        try:
            __import__(module)
            print(f"   ✅ {name}")
        except ImportError:
            print(f"   ⚠️  {name} - 未安装（可选）")
    
    return errors


def test_ffmpeg():
    """测试 FFmpeg"""
    print("\n🎬 测试 FFmpeg...")
    import subprocess
    try:
        result = subprocess.run(
            ['ffmpeg', '-version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            version = result.stdout.split('\n')[0]
            print(f"   ✅ {version[:50]}...")
            return []
    except FileNotFoundError:
        print("   ❌ ffmpeg 未安装")
        print("      安装: brew install ffmpeg")
        return ['ffmpeg']
    except Exception as e:
        print(f"   ❌ ffmpeg 检测失败: {e}")
        return ['ffmpeg']
    return []


def test_db_modules():
    """测试数据库模块"""
    print("\n🗄️  测试数据库模块...")
    
    errors = []
    modules = [
        'db.models',
        'db.schema',
        'db.repository',
        'db.search',
    ]
    
    for mod in modules:
        try:
            __import__(mod)
            print(f"   ✅ {mod}")
        except Exception as e:
            print(f"   ❌ {mod}: {e}")
            errors.append(mod)
    
    return errors


def main():
    """主函数"""
    print("━" * 40)
    print("🔬 环境测试")
    print("━" * 40)
    
    all_errors = []
    
    all_errors.extend(test_core_imports())
    all_errors.extend(test_ffmpeg())
    all_errors.extend(test_db_modules())
    
    print("\n" + "━" * 40)
    if all_errors:
        print(f"⚠️  发现 {len(all_errors)} 个问题: {all_errors}")
        print("请安装缺失的依赖后重试")
        return 1
    else:
        print("✅ 环境测试通过！")
        return 0


if __name__ == '__main__':
    sys.exit(main())
