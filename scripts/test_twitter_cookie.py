#!/usr/bin/env python3
"""
推特 Cookie 测试脚本
验证 browser_data 中的推特 Cookie 是否有效
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from DrissionPage import ChromiumOptions, ChromiumPage
import time


def test_twitter_cookies(browser_data_dir: str = "./browser_data"):
    """
    测试推特 Cookie 是否有效
    
    Args:
        browser_data_dir: 浏览器数据目录
    """
    print("=" * 60)
    print("推特 Cookie 测试")
    print("=" * 60)
    print()
    
    # 配置浏览器
    options = ChromiumOptions()
    options.set_user_data_path(browser_data_dir)
    options.headless(True)
    
    # 反爬虫配置
    options.set_argument('--no-sandbox')
    options.set_argument('--disable-blink-features=AutomationControlled')
    options.set_user_agent(
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    )
    
    page = ChromiumPage(options)
    
    try:
        # 访问推特首页
        print("🌐 正在访问推特首页...")
        page.get("https://twitter.com/home")
        time.sleep(3)
        
        # 获取所有 Cookies
        cookies = page.cookies()
        
        print(f"\n📊 找到 {len(cookies)} 个 Cookie")
        print()
        
        # 检查关键 Cookie
        key_cookies = ['auth_token', 'ct0', 'kdt', 'twid']
        found_keys = []
        
        for cookie in cookies:
            if cookie['name'] in key_cookies:
                found_keys.append(cookie['name'])
                value_preview = cookie['value'][:20] + "..." if len(cookie['value']) > 20 else cookie['value']
                print(f"  ✅ {cookie['name']}: {value_preview}")
        
        missing_keys = set(key_cookies) - set(found_keys)
        if missing_keys:
            print()
            print(f"  ⚠️  缺少关键 Cookie: {', '.join(missing_keys)}")
        
        # 检查是否已登录
        print()
        print("🔍 检查登录状态...")
        current_url = page.url
        
        if "login" in current_url or "unauthorized" in current_url:
            print("  ❌ 未登录或登录已过期")
            print("  💡 请运行: make login-twitter")
        else:
            print(f"  ✅ 已登录！当前页面: {current_url}")
            
            # 尝试获取用户名
            try:
                # 推特用户名通常在导航栏中
                user_elem = page.ele('tag:nav')
                if user_elem:
                    print("  ✅ 导航栏已加载，登录有效")
            except Exception:
                pass
        
        print()
        print("=" * 60)
        
        if found_keys and "login" not in current_url:
            print("✅ 推特 Cookie 有效")
            return True
        else:
            print("❌ 推特 Cookie 无效或已过期")
            return False
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        return False
    finally:
        page.quit()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="推特 Cookie 测试工具")
    parser.add_argument(
        "--browser-data-dir",
        default="./browser_data",
        help="浏览器数据目录（默认: ./browser_data）"
    )
    
    args = parser.parse_args()
    
    success = test_twitter_cookies(args.browser_data_dir)
    sys.exit(0 if success else 1)
