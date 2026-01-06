"""
检查小红书页面的图片元素
"""

import sys
from pathlib import Path

try:
    from DrissionPage import ChromiumOptions, ChromiumPage
except ImportError:
    print("❌ 错误: 请先安装 DrissionPage")
    sys.exit(1)


def check_xhs_images(url: str, browser_data_dir: str = "./browser_data"):
    """检查小红书页面的图片元素"""
    
    print("=" * 60)
    print("🔍 小红书图片元素检查工具")
    print("=" * 60)
    print()
    
    # 配置浏览器
    co = ChromiumOptions()
    co.set_user_data_path(browser_data_dir)
    co.headless(True)
    
    co.set_paths(browser_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
    co.set_argument('--no-sandbox')
    co.set_argument('--disable-blink-features=AutomationControlled')
    co.set_user_agent(
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    )
    
    print("🚀 正在启动浏览器...")
    page = ChromiumPage(addr_or_opts=co)
    
    try:
        print(f"📱 正在访问: {url}")
        page.get(url, timeout=30)
        print("⏳ 等待页面加载...")
        
        # 滚动加载图片
        for _ in range(3):
            page.scroll.to_bottom()
            page.wait(1)
        
        print()
        print("=" * 60)
        print("🖼️  图片元素分析")
        print("=" * 60)
        print()
        
        # 1. 检查 <img> 标签
        imgs = page.eles('tag:img')
        print(f"✓ 找到 {len(imgs)} 个 <img> 标签")
        for i, img in enumerate(imgs[:5], 1):
            src = img.attr('src') or img.attr('data-src') or img.attr('data-original')
            print(f"  {i}. src: {src[:80] if src else 'N/A'}...")
        
        print()
        
        # 2. 检查内容区域的HTML
        content_area = page.ele('#detail-desc', timeout=2)
        if content_area:
            html = content_area.html
            print(f"✓ 内容区域HTML长度: {len(html)} 字符")
            
            # 查找图片相关的属性
            import re
            
            # 查找所有可能的图片URL
            patterns = [
                (r'src="([^"]+\.(?:jpg|jpeg|png|webp|gif)[^"]*)"', 'src属性'),
                (r'data-src="([^"]+\.(?:jpg|jpeg|png|webp|gif)[^"]*)"', 'data-src属性'),
                (r'background-image:\s*url\(["\']?([^"\']+)["\']?\)', '背景图'),
                (r'https://[^\s"\'<>]+\.(?:jpg|jpeg|png|webp|gif)', 'URL模式')
            ]
            
            print()
            print("🔎 搜索图片URL模式:")
            for pattern, name in patterns:
                matches = re.findall(pattern, html, re.IGNORECASE)
                if matches:
                    print(f"\n  • {name}: 找到 {len(matches)} 个")
                    for j, match in enumerate(matches[:3], 1):
                        display = match[:80] if len(match) > 80 else match
                        print(f"    {j}. {display}")
        
        print()
        
        # 3. 检查特定的小红书图片容器
        xhs_containers = [
            '.note-slider',
            '.swiper-wrapper',
            '[class*="imageWrapper"]',
            '[class*="carousel"]',
            '[class*="slider"]'
        ]
        
        print("📦 检查小红书特定容器:")
        for selector in xhs_containers:
            elements = page.eles(selector)
            if elements:
                print(f"  ✓ {selector}: {len(elements)} 个")
                if elements:
                    html = elements[0].html[:500]
                    print(f"    HTML: {html}...")
        
        print()
        
        # 4. 打印完整的内容区域HTML（前1000字符）
        if content_area:
            print("=" * 60)
            print("📄 内容区域HTML示例（前1000字符）:")
            print("=" * 60)
            print(content_area.html[:1000])
            print("...")
            
    finally:
        page.quit()
        print()
        print("✓ 浏览器已关闭")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python scripts/check_xhs_images.py <URL>")
        sys.exit(1)
    
    url = sys.argv[1]
    check_xhs_images(url)
