#!/usr/bin/env python3
"""
推特(Twitter/X) 登录辅助脚本
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from DrissionPage import ChromiumOptions, ChromiumPage
import time


def login_twitter(browser_data_dir: str = "./browser_data"):
    """
    打开推特登录页面，等待用户手动登录
    
    Args:
        browser_data_dir: 浏览器数据目录
    """
    print("=" * 60)
    print("推特(Twitter/X) 登录助手")
    print("=" * 60)
    print()
    print("🔐 即将打开推特登录页面，请手动完成以下操作：")
    print("   1. 输入你的用户名/邮箱和密码")
    print("   2. 完成任何验证码或安全验证")
    print("   3. 登录成功后，浏览几个推文确保登录状态正常")
    print("   4. 回到终端，按 Enter 键关闭浏览器")
    print()
    print("💡 登录信息会自动保存到:", browser_data_dir)
    print()
    
    # 配置浏览器
    options = ChromiumOptions()
    options.set_user_data_path(browser_data_dir)
    options.headless(False)  # 必须显示浏览器
    
    # 反爬虫配置
    options.set_argument('--no-sandbox')
    options.set_argument('--disable-blink-features=AutomationControlled')
    options.set_user_agent(
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    )
    
    # 打开浏览器
    page = ChromiumPage(options)
    
    try:
        # 访问推特登录页
        print("🌐 正在打开推特登录页...")
        page.get("https://twitter.com/login")
        
        # 等待用户操作
        input("\n✅ 登录完成后，按 Enter 键关闭浏览器...")
        
        # 验证登录状态
        print("\n🔍 正在验证登录状态...")
        page.get("https://twitter.com/home")
        time.sleep(3)
        
        # 检查是否还在登录页
        current_url = page.url
        if "login" in current_url:
            print("⚠️  警告：似乎还未成功登录，请重试")
        else:
            print("✅ 登录成功！Cookie 已保存")
            print(f"📁 数据目录: {browser_data_dir}")
        
    except KeyboardInterrupt:
        print("\n\n👋 已取消登录")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
    finally:
        page.quit()


def export_cookies_to_file(browser_data_dir: str = "./browser_data", output_file: str = "cookies/twitter.txt"):
    """
    从浏览器数据目录导出推特 Cookies 到文件
    
    Args:
        browser_data_dir: 浏览器数据目录
        output_file: 输出文件路径
    """
    print("\n" + "=" * 60)
    print("导出推特 Cookies")
    print("=" * 60)
    
    # 配置浏览器
    options = ChromiumOptions()
    options.set_user_data_path(browser_data_dir)
    options.headless(True)
    
    page = ChromiumPage(options)
    
    try:
        # 访问推特首页以触发 Cookie 加载
        page.get("https://twitter.com")
        time.sleep(2)
        
        # 获取所有 Cookies
        cookies = page.cookies()
        
        if not cookies:
            print("❌ 未找到 Cookies，请先登录")
            return
        
        # 保存到文件
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            for cookie in cookies:
                # Netscape Cookie 格式
                f.write(f"{cookie['domain']}\t")
                f.write(f"TRUE\t")
                f.write(f"{cookie['path']}\t")
                f.write(f"{'TRUE' if cookie.get('secure', False) else 'FALSE'}\t")
                f.write(f"{cookie.get('expiry', 0)}\t")
                f.write(f"{cookie['name']}\t")
                f.write(f"{cookie['value']}\n")
        
        print(f"✅ Cookies 已导出到: {output_path}")
        print(f"📊 共 {len(cookies)} 个 Cookie")
        
    except Exception as e:
        print(f"❌ 导出失败: {e}")
    finally:
        page.quit()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="推特登录辅助工具")
    parser.add_argument(
        "--export",
        action="store_true",
        help="导出 Cookies 到文件"
    )
    parser.add_argument(
        "--browser-data-dir",
        default="./browser_data",
        help="浏览器数据目录（默认: ./browser_data）"
    )
    parser.add_argument(
        "--output",
        default="cookies/twitter.txt",
        help="Cookie 输出文件（默认: cookies/twitter.txt）"
    )
    
    args = parser.parse_args()
    
    if args.export:
        export_cookies_to_file(args.browser_data_dir, args.output)
    else:
        login_twitter(args.browser_data_dir)
