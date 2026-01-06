#!/usr/bin/env python3
"""
测试Cookie统一管理功能
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_cookie_manager():
    """测试Cookie管理器"""
    print("=" * 60)
    print("测试 Cookie 统一管理")
    print("=" * 60)
    
    from archiver.utils.cookie_manager import (
        CookieManager, 
        get_xiaohongshu_cookies
    )
    
    # 测试1: 基本功能
    print("\n1. 测试 CookieManager 初始化")
    manager = CookieManager()
    print("   ✓ CookieManager 创建成功")
    
    # 测试2: XHS配置加载
    print("\n2. 测试 XHS-Downloader 配置加载")
    cookies = manager.load_from_xhs_config()
    
    if cookies:
        print(f"   ✓ 成功加载 XHS Cookie")
        print(f"   ✓ 包含 {len(cookies)} 个字段")
        
        # 显示部分Cookie（安全）
        if 'web_session' in cookies:
            session = cookies['web_session']
            print(f"   ✓ web_session: {session[:20]}... (已隐藏)")
    else:
        print("   ⚠️  未找到 XHS Cookie 配置")
        print("   💡 运行: make config-xhs-cookie")
    
    # 测试3: 便捷函数
    print("\n3. 测试便捷函数 get_xiaohongshu_cookies()")
    cookies = get_xiaohongshu_cookies()
    
    if cookies:
        print(f"   ✓ 成功获取小红书 Cookie")
        print(f"   ✓ 字段数: {len(cookies)}")
    else:
        print("   ⚠️  未获取到 Cookie")
    
    # 测试4: 配置文件检查
    print("\n4. 检查配置文件")
    config_path = Path(__file__).parent.parent / "XHS-Downloader" / "Volume" / "settings.json"
    
    if config_path.exists():
        print(f"   ✓ 配置文件存在: {config_path}")
        
        import json
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        has_cookie = bool(config.get('cookie'))
        has_ua = bool(config.get('user_agent'))
        
        print(f"   {'✓' if has_cookie else '✗'} cookie: {'已配置' if has_cookie else '未配置'}")
        print(f"   {'✓' if has_ua else '✗'} user_agent: {'已配置' if has_ua else '未配置'}")
    else:
        print(f"   ✗ 配置文件不存在: {config_path}")
        print("   💡 运行: make config-xhs-cookie")
    
    print("\n" + "=" * 60)
    
    return cookies is not None


def test_integration():
    """测试与归档模块的集成"""
    print("\n" + "=" * 60)
    print("测试归档模块集成")
    print("=" * 60)
    
    from archiver.utils.url_parser import detect_platform
    
    # 测试平台检测
    print("\n1. 测试平台检测")
    test_urls = {
        "https://www.xiaohongshu.com/explore/abc123": "xiaohongshu",
        "https://www.zhihu.com/question/123": "zhihu",
    }
    
    for url, expected in test_urls.items():
        platform = detect_platform(url)
        status = "✓" if platform == expected else "✗"
        print(f"   {status} {url[:50]} → {platform}")
    
    # 测试自动Cookie加载
    print("\n2. 测试自动Cookie加载（模拟）")
    from archiver.utils.cookie_manager import get_xiaohongshu_cookies
    
    cookies = get_xiaohongshu_cookies()
    if cookies:
        print("   ✓ 小红书Cookie可用")
        print("   ✓ 归档模块会自动使用此Cookie")
    else:
        print("   ⚠️  小红书Cookie不可用")
        print("   💡 需要配置：make config-xhs-cookie")
    
    print("\n" + "=" * 60)


def main():
    """主函数"""
    print("\n🔍 Cookie 统一管理测试\n")
    
    try:
        # 测试Cookie管理
        has_config = test_cookie_manager()
        
        # 测试集成
        test_integration()
        
        # 总结
        print("\n" + "=" * 60)
        print("总结")
        print("=" * 60)
        
        if has_config:
            print("✓ Cookie配置正常")
            print("✓ 归档模块可以使用小红书Cookie")
            print("\n使用方式：")
            print("  make archive URL=https://www.xiaohongshu.com/explore/xxx")
        else:
            print("⚠️  Cookie未配置")
            print("\n配置步骤：")
            print("  1. 运行: make config-xhs-cookie")
            print("  2. 按提示粘贴Cookie")
            print("  3. 配置后即可使用")
        
        print("\n特点：")
        print("  • 统一管理：视频下载和网页归档共享Cookie")
        print("  • 自动检测：检测到小红书URL自动使用Cookie")
        print("  • 一次配置：配置一次，两处使用")
        
        print("\n" + "=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
