"""
分析小红书图片和文字的公共父容器
"""

import sys
from DrissionPage import ChromiumOptions, ChromiumPage

def analyze_parent(url: str, browser_data_dir: str = "./browser_data"):
    co = ChromiumOptions()
    co.set_user_data_path(browser_data_dir)
    co.headless(True)
    # co.headless(False) # 调试时可开启
    co.set_paths(browser_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
    
    page = ChromiumPage(addr_or_opts=co)
    
    try:
        print(f"正在访问: {url}")
        page.get(url)
        page.wait(3)
        
        # 定位图片容器 (根据用户提供的线索)
        img_container = page.ele('.swiper-wrapper')
        if not img_container:
            # 备选图片容器
            img_container = page.ele('.note-slider')
        
        # 定位文字容器
        text_container = page.ele('#detail-desc')
        if not text_container:
            text_container = page.ele('.note-content')
            
        print(f"图片容器找到: {'是' if img_container else '否'}")
        print(f"文字容器找到: {'是' if text_container else '否'}")
        
        if img_container and text_container:
            # 寻找公共父级
            parent = img_container.parent()
            levels = 1
            found = False
            
            while parent and levels < 10:
                # 检查是否包含文字容器
                html = parent.html
                if 'id="detail-desc"' in html or 'class="note-content"' in html:
                    print(f"\n找到公共父级 (向上 {levels} 层):")
                    print(f"标签: {parent.tag}")
                    print(f"Class: {parent.attr('class')}")
                    print(f"ID: {parent.attr('id')}")
                    found = True
                    break
                
                parent = parent.parent()
                levels += 1
            
            if not found:
                print("未找到近距离的公共父级")
        else:
            # 打印页面结构辅助调试
            print("\n页面关键结构:")
            main = page.ele('main')
            if main:
                print(f"Main content: {main.html[:500]}...")
            
    finally:
        page.quit()

if __name__ == "__main__":
    url = "https://www.xiaohongshu.com/discovery/item/6958dc6f000000002203209f?source=webshare&xhsshare=pc_web&xsec_token=ABjvlDsTc0Lpd4z4AeQ1ERlRL5DpU97JA67t4QXjZrK20=&xsec_source=pc_share"
    analyze_parent(url)
