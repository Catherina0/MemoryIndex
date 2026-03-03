import argparse
from DrissionPage import ChromiumOptions, ChromiumPage
from pathlib import Path
import sys

def get_page(data_dir: str = "./browser_data"):
    co = ChromiumOptions()
    project_chromium = Path(__file__).parent.parent / "chromium/chrome-mac/Chromium.app/Contents/MacOS/Chromium"
    if project_chromium.exists():
        co.set_paths(browser_path=str(project_chromium))
    else:
        co.set_paths(browser_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
    
    co.set_user_data_path(data_dir)
    co.headless(True)
    return ChromiumPage(addr_or_opts=co)

def list_cookies(page):
    res = page.run_cdp('Network.getAllCookies')
    cookies = res.get('cookies', [])
    domains = {}
    for c in cookies:
        domain = c.get('domain', '')
        if domain.startswith('.'):
            domain = domain[1:]
        domains[domain] = domains.get(domain, 0) + 1
    
    print("\n" + "=" * 40)
    print("🍪 当前保存的 Cookie 统计:")
    print("=" * 40)
    if not domains:
        print("暂无任何 Cookie 数据")
    else:
        for domain, count in sorted(domains.items(), key=lambda x: x[1], reverse=True):
            print(f" 🌐 {domain} : {count} 个")
    print("-" * 40)
    print(f"总计: {len(cookies)} 个 Cookies\n")

def delete_cookie(page, domain_keyword):
    print(f"\n🔍 正在查找包含 '{domain_keyword}' 的 Cookie...")
    res = page.run_cdp('Network.getAllCookies')
    cookies = res.get('cookies', [])
    deleted = 0
    domains_affected = set()
    
    for c in cookies:
        if domain_keyword in c.get('domain', ''):
            # Network.deleteCookies needs name and (url or domain structure)
            # URL is required by CDP for accurate deletion when using name.
            # Construct a dummy URL based on domain and secure flag.
            domain = c['domain']
            protocol = "https" if c.get('secure') else "http"
            url = f"{protocol}://{domain.lstrip('.')}{c['path']}"
            page.run_cdp('Network.deleteCookies', name=c['name'], url=url, domain=c['domain'], path=c['path'])
            deleted += 1
            domains_affected.add(c.get('domain'))
            
    if deleted > 0:
        print(f"✅ 成功删除了 {deleted} 个 Cookie")
        print(f"📂 涉及域名: {', '.join(domains_affected)}\n")
    else:
        print(f"⚠️ 未找到匹配 '{domain_keyword}' 的 Cookie\n")

def clear_all(page):
    page.run_cdp('Network.clearBrowserCookies')
    print("\n✅ 已清除浏览器中所有的 Cookie\n")

def main():
    parser = argparse.ArgumentParser(description="Cookie 管理工具")
    parser.add_argument("--list", action="store_true", help="列出所有 Cookie 的域名统计")
    parser.add_argument("--delete", type=str, metavar="DOMAIN", help="删除包含指定域名的所有 Cookie (如 xiaohongshu.com)")
    parser.add_argument("--clear-all", action="store_true", help="清除所有 Cookie")
    
    args = parser.parse_args()
    
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)
        
    print("🚀 正在启动浏览器...")
    page = None
    try:
        page = get_page()
        
        if args.clear_all:
            clear_all(page)
        elif args.delete:
            delete_cookie(page, args.delete)
        elif args.list:
            list_cookies(page)
            
    except Exception as e:
        print(f"\n❌ 操作失败: {e}")
    finally:
        if page:
            page.quit()

if __name__ == "__main__":
    main()