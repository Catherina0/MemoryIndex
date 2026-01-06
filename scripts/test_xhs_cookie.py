"""
测试小红书 Cookie 是否正确获取
"""

import sys
from pathlib import Path

try:
    from DrissionPage import ChromiumOptions, ChromiumPage
except ImportError:
    print("❌ 错误: 请先安装 DrissionPage")
    print("运行: pip install DrissionPage")
    sys.exit(1)


def test_xhs_cookies(browser_data_dir: str = "./browser_data"):
    """
    测试小红书的 Cookie 是否正确获取
    
    Args:
        browser_data_dir: 浏览器数据目录
    """
    print("=" * 60)
    print("🧪 小红书 Cookie 测试工具")
    print("=" * 60)
    print()
    
    # 检查目录是否存在
    if not Path(browser_data_dir).exists():
        print(f"❌ 浏览器数据目录不存在: {browser_data_dir}")
        print("💡 请先运行 'make login' 完成登录")
        return False
    
    print(f"✓ 浏览器数据目录: {browser_data_dir}")
    print()
    
    # 配置浏览器
    co = ChromiumOptions()
    co.set_user_data_path(browser_data_dir)
    co.headless(True)  # 无头模式
    
    # 明确指定浏览器路径（macOS）
    co.set_paths(browser_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
    
    # 反爬虫配置
    co.set_argument('--no-sandbox')
    co.set_argument('--disable-blink-features=AutomationControlled')
    co.set_user_agent(
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    )
    
    print("🚀 正在启动浏览器...")
    try:
        page = ChromiumPage(addr_or_opts=co)
        page.get('about:blank')
        print("✓ 浏览器启动成功")
        print()
    except Exception as e:
        print(f"❌ 浏览器启动失败: {e}")
        return False
    
    try:
        # 访问小红书
        print("📱 正在访问小红书...")
        page.get('https://www.xiaohongshu.com/', timeout=30)
        print("✓ 页面加载完成")
        print()
        
        # 获取所有 Cookie
        print("🍪 正在检查 Cookie...")
        cookies = page.cookies(all_domains=False)
        
        if not cookies:
            print("❌ 未找到任何 Cookie")
            print("💡 请运行 'make login' 重新登录")
            return False
        
        print(f"✓ 找到 {len(cookies)} 个 Cookie")
        print()
        
        # 检查关键 Cookie
        print("🔍 关键 Cookie 检查：")
        key_cookies = ['web_session', 'webId', 'a1', 'webBuild']
        found_keys = []
        
        for cookie in cookies:
            name = cookie.get('name', '')
            if name in key_cookies:
                value = cookie.get('value', '')
                # 只显示前10个字符，保护隐私
                display_value = value[:10] + "..." if len(value) > 10 else value
                print(f"   ✓ {name}: {display_value}")
                found_keys.append(name)
        
        print()
        
        # 判断登录状态
        if 'web_session' in found_keys or 'a1' in found_keys:
            print("✅ Cookie 状态: 正常 (已登录)")
            print()
            print("💡 所有关键 Cookie:")
            for cookie in cookies:
                name = cookie.get('name', '')
                value = cookie.get('value', '')
                domain = cookie.get('domain', '')
                # 显示前20个字符
                display_value = value[:20] + "..." if len(value) > 20 else value
                print(f"   • {name}: {display_value}")
                print(f"     域名: {domain}")
            return True
        else:
            print("⚠️  Cookie 状态: 可能未登录")
            print("💡 建议运行 'make login' 重新登录")
            print()
            print("📋 现有 Cookie:")
            for cookie in cookies:
                name = cookie.get('name', '')
                value = cookie.get('value', '')
                display_value = value[:20] + "..." if len(value) > 20 else value
                print(f"   • {name}: {display_value}")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        page.quit()
        print()
        print("✓ 浏览器已关闭")


if __name__ == "__main__":
    browser_data_dir = sys.argv[1] if len(sys.argv) > 1 else "./browser_data"
    success = test_xhs_cookies(browser_data_dir)
    sys.exit(0 if success else 1)
