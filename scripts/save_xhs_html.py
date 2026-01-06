"""
保存小红书页面的完整HTML用于分析
"""

import sys
from DrissionPage import ChromiumOptions, ChromiumPage


def save_xhs_html(url: str, output_file: str = "xhs_page.html", browser_data_dir: str = "./browser_data"):
    """保存小红书页面的HTML"""
    
    co = ChromiumOptions()
    co.set_user_data_path(browser_data_dir)
    co.headless(True)
    co.set_paths(browser_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
    co.set_argument('--no-sandbox')
    co.set_argument('--disable-blink-features=AutomationControlled')
    
    page = ChromiumPage(addr_or_opts=co)
    
    try:
        print(f"访问: {url}")
        page.get(url, timeout=30)
        
        # 等待内容加载
        page.wait(3)
        
        # 滚动一次
        page.scroll.to_bottom()
        page.wait(2)
        page.scroll.to_top()
        page.wait(1)
        
        # 保存HTML
        html = page.html
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"✓ HTML已保存到: {output_file}")
        print(f"  文件大小: {len(html)} 字符")
        
        # 统计图片
        import re
        img_urls = re.findall(r'https://sns-webpic-qc\.xhscdn\.com/[^\s"\'<>]+', html)
        img_urls_unique = list(set([url for url in img_urls if 'avatar' not in url]))
        
        print(f"  内容图片: {len(img_urls_unique)} 张")
        
        if img_urls_unique:
            print("\n图片URL:")
            for i, url in enumerate(img_urls_unique[:10], 1):
                print(f"  {i}. {url}")
        
    finally:
        page.quit()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python scripts/save_xhs_html.py <URL> [output_file]")
        sys.exit(1)
    
    url = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "xhs_page.html"
    save_xhs_html(url, output_file)
