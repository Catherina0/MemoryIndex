"""
精确定位小红书笔记内容和图片
"""

import sys
from DrissionPage import ChromiumOptions, ChromiumPage


def locate_xhs_content(url: str, browser_data_dir: str = "./browser_data"):
    """精确定位小红书笔记的内容和图片"""
    
    co = ChromiumOptions()
    co.set_user_data_path(browser_data_dir)
    co.headless(True)
    co.set_paths(browser_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
    co.set_argument('--no-sandbox')
    co.set_argument('--disable-blink-features=AutomationControlled')
    
    page = ChromiumPage(addr_or_opts=co)
    
    try:
        page.get(url, timeout=30)
        
        # 滚动加载
        for _ in range(2):
            page.scroll.to_bottom()
            page.wait(1)
        page.scroll.to_top()
        
        print("=" * 80)
        print("🔍 小红书笔记内容定位")
        print("=" * 80)
        
        # 查找笔记主体容器
        note_selectors = [
            ('.note-content', '笔记内容'),
            ('[class*="noteContainer"]', '笔记容器'),
            ('[class*="detail"]', '详情容器'),
            ('.post-content', '帖子内容'),
        ]
        
        for selector, desc in note_selectors:
            elem = page.ele(selector, timeout=1)
            if elem:
                print(f"\n✓ 找到 {desc} ({selector})")
                
                # 检查这个容器里的图片
                imgs = elem.eles('tag:img')
                print(f"  包含 {len(imgs)} 个图片")
                
                for i, img in enumerate(imgs[:5], 1):
                    src = img.attr('src')
                    if src and 'xhscdn.com' in src:
                        print(f"  {i}. {src[:80]}...")
                
                # 打印HTML的前500字符
                html = elem.html
                print(f"  HTML长度: {len(html)} 字符")
                print(f"  HTML示例: {html[:300]}...")
                print()
        
        # 专门查找 carousel/swiper (通常是图片轮播)
        print("=" * 80)
        print("🎠 查找图片轮播容器")
        print("=" * 80)
        
        carousel = page.ele('.carousel, .swiper, [class*="Carousel"], [class*="slider"]', timeout=1)
        if carousel:
            print("\n✓ 找到轮播容器")
            imgs = carousel.eles('tag:img')
            print(f"  包含 {len(imgs)} 个图片")
            
            for i, img in enumerate(imgs, 1):
                src = img.attr('src')
                if src and 'xhscdn.com' in src and 'avatar' not in src:
                    print(f"  {i}. {src}")
        else:
            print("\n✗ 未找到轮播容器")
        
        # 查找文字内容
        print("\n" + "=" * 80)
        print("📝 查找文字内容")
        print("=" * 80)
        
        text_elem = page.ele('#detail-desc', timeout=2)
        if text_elem:
            text = text_elem.text
            print(f"\n✓ #detail-desc: {len(text)} 字符")
            print(f"  内容: {text[:200]}...")
        
        # 检查是否有单独的图片容器（与文字分离）
        print("\n" + "=" * 80)
        print("🎯 推荐方案")
        print("=" * 80)
        
        # 方案：找笔记的主容器
        main_container_selectors = [
            '.note-detail',
            '[class*="NoteDetail"]',
            '#app > div > div[class*="container"]',
            'main',
        ]
        
        for selector in main_container_selectors:
            elem = page.ele(selector, timeout=1)
            if elem:
                imgs = elem.eles('tag:img')
                xhs_imgs = [img for img in imgs if img.attr('src') and 'xhscdn.com' in img.attr('src') and 'avatar' not in img.attr('src')]
                
                if len(xhs_imgs) >= 10:  # 找到了包含大量图片的容器
                    print(f"\n✅ 推荐使用选择器: {selector}")
                    print(f"   包含 {len(xhs_imgs)} 张内容图片")
                    print(f"   HTML长度: {len(elem.html)} 字符")
                    
                    # 打印前3张图片URL
                    for i, img in enumerate(xhs_imgs[:3], 1):
                        print(f"   {i}. {img.attr('src')}")
                    break
        
    finally:
        page.quit()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python scripts/locate_xhs_content.py <URL>")
        sys.exit(1)
    
    url = sys.argv[1]
    locate_xhs_content(url)
