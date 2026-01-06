"""
详细检查小红书页面结构
"""

import sys
from pathlib import Path

try:
    from DrissionPage import ChromiumOptions, ChromiumPage
except ImportError:
    print("❌ 错误: 请先安装 DrissionPage")
    sys.exit(1)


def analyze_xhs_structure(url: str, browser_data_dir: str = "./browser_data"):
    """分析小红书页面结构"""
    
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
    
    page = ChromiumPage(addr_or_opts=co)
    
    try:
        page.get(url, timeout=30)
        
        # 滚动加载
        for _ in range(3):
            page.scroll.to_bottom()
            page.wait(1)
        
        print("=" * 80)
        print("小红书页面结构分析")
        print("=" * 80)
        
        # 1. 检查#detail-desc区域的图片
        detail_desc = page.ele('#detail-desc', timeout=2)
        if detail_desc:
            imgs_in_desc = detail_desc.eles('tag:img')
            print(f"\n✓ #detail-desc 区域: 找到 {len(imgs_in_desc)} 个图片")
            if imgs_in_desc:
                for i, img in enumerate(imgs_in_desc[:3], 1):
                    src = img.attr('src')
                    print(f"  {i}. {src}")
        
        # 2. 查找图片轮播容器
        carousel_selectors = [
            ('.carousel', '轮播容器'),
            ('.swiper-wrapper', 'Swiper包装器'),
            ('[class*="slider"]', 'Slider容器'),
            ('[class*="carousel"]', 'Carousel容器'),
            ('[class*="imageWrapper"]', '图片包装器'),
        ]
        
        print(f"\n" + "=" * 80)
        print("🔍 查找图片容器:")
        print("=" * 80)
        
        for selector, desc in carousel_selectors:
            elements = page.eles(selector)
            if elements:
                print(f"\n✓ {desc} ({selector}): {len(elements)} 个")
                for i, elem in enumerate(elements[:2], 1):
                    imgs = elem.eles('tag:img')
                    print(f"  容器 {i}: {len(imgs)} 个图片")
                    for j, img in enumerate(imgs[:3], 1):
                        src = img.attr('src')
                        if src and 'xhscdn.com' in src:
                            print(f"    图片 {j}: {src[:100]}...")
        
        # 3. 直接查找所有包含xhscdn.com的图片
        print(f"\n" + "=" * 80)
        print("🖼️  所有小红书CDN图片:")
        print("=" * 80)
        
        all_imgs = page.eles('tag:img')
        xhs_imgs = []
        for img in all_imgs:
            src = img.attr('src')
            if src and 'xhscdn.com' in src and 'avatar' not in src:
                xhs_imgs.append(src)
        
        print(f"\n找到 {len(xhs_imgs)} 个内容图片（排除头像）:")
        for i, src in enumerate(xhs_imgs, 1):
            print(f"{i}. {src}")
        
        # 4. 检查父容器结构
        if xhs_imgs and all_imgs:
            print(f"\n" + "=" * 80)
            print("📦 图片父容器分析:")
            print("=" * 80)
            
            # 找到第一个内容图片的元素
            for img in all_imgs:
                src = img.attr('src')
                if src and src in xhs_imgs[:1]:
                    print(f"\n图片 URL: {src}")
                    
                    # 打印父级元素链
                    current = img
                    level = 0
                    while current and level < 5:
                        tag = current.tag
                        classes = current.attr('class') or ''
                        id_attr = current.attr('id') or ''
                        print(f"  {'  ' * level}↑ <{tag}> id='{id_attr}' class='{classes[:50]}'")
                        current = current.parent()
                        level += 1
                    break
            
    finally:
        page.quit()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python scripts/analyze_xhs_structure.py <URL>")
        sys.exit(1)
    
    url = sys.argv[1]
    analyze_xhs_structure(url)
