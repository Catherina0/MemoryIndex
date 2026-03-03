"""
浏览器登录辅助脚本
用于一次性完成各平台的登录，保存登录态到 browser_data
"""

import sys
import time
from pathlib import Path

try:
    from DrissionPage import ChromiumOptions, ChromiumPage
except ImportError:
    print("错误: 请先安装 DrissionPage")
    print("运行: pip install DrissionPage")
    sys.exit(1)


def login_helper(browser_data_dir: str = "./browser_data"):
    """
    打开浏览器供用户手动登录
    
    Args:
        browser_data_dir: 浏览器数据目录
    """
    # 确保目录存在
    Path(browser_data_dir).mkdir(parents=True, exist_ok=True)
    
    # 配置浏览器
    co = ChromiumOptions()
    co.set_user_data_path(browser_data_dir)
    co.headless(False)  # 必须显示窗口
    
    # 明确指定浏览器路径（macOS）
    project_chromium = Path(__file__).parent.parent / "chromium/chrome-mac/Chromium.app/Contents/MacOS/Chromium"
    if project_chromium.exists():
        co.set_paths(browser_path=str(project_chromium))
    else:
        co.set_paths(browser_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
    
    # 反爬虫配置
    co.set_argument('--no-sandbox')
    co.set_argument('--disable-blink-features=AutomationControlled')
    co.set_user_agent(
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    )
    
    print("=" * 60)
    print("🌐 浏览器登录辅助工具")
    print("=" * 60)
    print()
    print("浏览器窗口将打开，请在窗口中完成以下操作：")
    print()
    print("1. 访问需要归档的平台（知乎/小红书/B站等）")
    print("2. 点击登录，完成登录流程")
    print("3. 勾选 '记住我' 或 '自动登录'")
    print("4. 确认登录成功后，关闭浏览器或按 Ctrl+C")
    print()
    print("⚠️  注意：")
    print("   - 登录数据会自动保存到: " + browser_data_dir)
    print("   - 下次归档时会自动使用这些登录态")
    print("   - 如需重新登录，运行 'make reset-browser'")
    print()
    print("=" * 60)
    print("正在启动 Chrome 浏览器...")
    try:
        page = ChromiumPage(addr_or_opts=co)
        # 给浏览器足够时间完全启动并建立连接
        # time.sleep(3)
        # 打开初始页面以确保连接稳定
        page.get('about:blank')
        time.sleep(1)
    except Exception as e:
        print(f"\n❌ 浏览器启动失败: {e}")
        print("\n💡 可能的原因：")
        print("   1. Chrome 浏览器未安装")
        print("   2. Chrome 路径不正确")
        print("   3. 端口被占用")
        print("\n请检查后重试。")
        sys.exit(1)
    
    print("✓ 浏览器已启动")
    print()
    print("📋 推荐平台列表：")
    print("   1 - 知乎 (zhihu.com)")
    print("   2 - 小红书 (xiaohongshu.com)")
    print("   3 - 哔哩哔哩 (bilibili.com)")
    print("   0 - 手动输入网址")
    print()
    
    try:
        choice = input("请选择平台 [1-3] 或按 0 手动输入 (直接按 Enter 跳过): ").strip()
        
        url_to_open = None
        if choice == "1":
            print("\n正在打开知乎...")
            url_to_open = "https://www.zhihu.com/"
        elif choice == "2":
            print("\n正在打开小红书...")
            url_to_open = "https://www.xiaohongshu.com/"
        elif choice == "3":
            print("\n正在打开哔哩哔哩...")
            url_to_open = "https://www.bilibili.com/"
        elif choice == "0":
            url_to_open = input("请输入网址 (例如: https://example.com): ").strip()
            if url_to_open:
                print(f"\n正在打开 {url_to_open}...")
        
        # 打开网页并等待加载
        if url_to_open:
            try:
                page.get(url_to_open, timeout=30)
                print("⏳ 等待页面加载...")
                time.sleep(3)  # 等待页面完全加载
                print("✓ 页面加载完成")
            except Exception as e:
                print(f"⚠️  页面加载出现问题: {e}")
                print("💡 浏览器窗口应该已经打开，请手动访问需要登录的网站")
        else:
            print("\n💡 提示: 请在浏览器地址栏手动输入网址")
        
        print()
        print("=" * 60)
        print("📝 操作步骤：")
        print("   1. 在浏览器中完成登录")
        print("   2. 勾选 '记住我' 或 '自动登录'")
        print("   3. 确认能正常访问内容后")
        print("   4. 回到终端按 Enter 键保存并退出")
        print("=" * 60)
        print()
        
        input("✋ 完成登录后，按 Enter 键保存登录态...")
        
        # 验证登录状态
        print("\n🔍 正在验证登录状态...")
        
        try:
            # 简单的验证逻辑：刷新页面或访问首页，看是否跳转回登录页
            current_url = page.url
            verified = True
            platform_name = "未知平台"
            
            if "zhihu.com" in current_url:
                platform_name = "知乎"
                print(f"   正在检查 {platform_name} 登录状态...")
                page.get("https://www.zhihu.com/follow")
                time.sleep(2)
                if "signin" in page.url or "login" in page.url:
                    verified = False
                    
            elif "bilibili.com" in current_url:
                platform_name = "哔哩哔哩"
                print(f"   正在检查 {platform_name} 登录状态...")
                page.get("https://account.bilibili.com/account/home")
                time.sleep(2)
                if "passport.bilibili.com" in page.url:
                    verified = False
                    
            elif "xiaohongshu.com" in current_url:
                platform_name = "小红书"
                print(f"   正在检查 {platform_name} 登录状态...")
                # 小红书主要检查 Cookie
                raw_cookies = page.cookies()
                has_session = False
                if isinstance(raw_cookies, dict):
                    has_session = any("session" in k for k in raw_cookies)
                elif isinstance(raw_cookies, list):
                    has_session = any(isinstance(c, dict) and "session" in c.get("name", "") for c in raw_cookies)
                
                if not has_session:
                    print("   ⚠️  Warning: 未检测到 session 相关 Cookie")
                # 刷新页面确保没弹窗
                page.refresh()
                time.sleep(2)
                
            elif "twitter.com" in current_url or "x.com" in current_url:
                platform_name = "Twitter/X"
                print(f"   正在检查 {platform_name} 登录状态...")
                page.get("https://twitter.com/home")
                time.sleep(3)
                if "login" in page.url or "i/flow/login" in page.url:
                    verified = False
            
            if verified:
                print(f"✅ 验证通过：{platform_name} 登录状态看似正常")
            else:
                print(f"⚠️  警告：检测到可能未成功登录 {platform_name}（页面发生了跳转）")
                print("   如果确认已登录，请忽略此提示。")
        except Exception as e:
            print(f"⚠️  验证过程中出现错误（不影响保存）: {e}")
            
        print()
        print("✓ 登录数据已保存到: " + browser_data_dir)
        print("✓ 现在可以使用 'make archive URL=...' 归档内容了！")
        
    except KeyboardInterrupt:
        print("\n\n✓ 登录数据已保存")
    finally:
        page.quit()
        print("✓ 浏览器已关闭")


if __name__ == "__main__":
    # 从命令行参数获取浏览器数据目录
    browser_data_dir = sys.argv[1] if len(sys.argv) > 1 else "./browser_data"
    login_helper(browser_data_dir)
