"""
分析小红书页面中作者信息和正文的结构关系
"""

from DrissionPage import ChromiumOptions, ChromiumPage

def analyze_xhs_structure():
    url = "https://www.xiaohongshu.com/discovery/item/6958dc6f000000002203209f"
    
    co = ChromiumOptions()
    co.set_user_data_path("./browser_data")
    co.headless(True)
    co.set_paths(browser_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
    
    page = ChromiumPage(addr_or_opts=co)
    
    try:
        page.get(url)
        page.wait(3)
        
        print("=" * 80)
        print("分析小红书页面结构")
        print("=" * 80)
        
        # 1. 查找正文内容
        detail_desc = page.ele('#detail-desc')
        if detail_desc:
            text = detail_desc.text
            print(f"\n✓ 找到正文区域 (#detail-desc): {len(text)} 字符")
            print(f"  内容预览: {text[:100]}...")
            print(f"  父级: {detail_desc.parent().tag} class='{detail_desc.parent().attr('class')}'")
        
        # 2. 查找作者信息
        author_selectors = [
            ('[class*="author"]', '作者容器'),
            ('[class*="user-info"]', '用户信息'),
            ('a[href*="/user/profile"]', '用户链接'),
            ('[class*="name"]', '名字'),
        ]
        
        print(f"\n" + "=" * 80)
        print("查找作者相关元素:")
        print("=" * 80)
        
        for selector, desc in author_selectors:
            elements = page.eles(selector)
            if elements:
                print(f"\n✓ {desc} ({selector}): {len(elements)} 个")
                for i, elem in enumerate(elements[:2], 1):
                    text = elem.text[:50] if elem.text else '<no text>'
                    classes = elem.attr('class') or ''
                    print(f"  {i}. text='{text}' class='{classes}'")
                    
                    # 检查是否包含正文
                    html = elem.html
                    if detail_desc and 'detail-desc' in html:
                        print(f"     ⚠️  此元素包含正文！")
        
        # 3. 查找"关注"按钮
        print(f"\n" + "=" * 80)
        print("查找关注按钮:")
        print("=" * 80)
        
        follow_elements = []
        for elem in page.eles('tag:button'):
            if '关注' in elem.text:
                follow_elements.append(elem)
        
        for elem in page.eles('tag:div'):
            if elem.text == '关注':
                follow_elements.append(elem)
        
        if follow_elements:
            print(f"\n✓ 找到 {len(follow_elements)} 个关注按钮")
            for i, elem in enumerate(follow_elements, 1):
                classes = elem.attr('class') or ''
                print(f"  {i}. <{elem.tag}> class='{classes}'")
                parent = elem.parent()
                print(f"     父级: <{parent.tag}> class='{parent.attr('class')}'")
        
        # 4. 完整的 #noteContainer 结构
        print(f"\n" + "=" * 80)
        print("#noteContainer 的直接子元素:")
        print("=" * 80)
        
        note_container = page.ele('#noteContainer')
        if note_container:
            children = note_container.children()
            for i, child in enumerate(children[:10], 1):
                classes = child.attr('class') or ''
                text_preview = child.text[:50] if child.text else ''
                print(f"{i}. <{child.tag}> class='{classes}'")
                print(f"   text: {text_preview}...")
                
                # 检查是否包含正文
                html = child.html
                if 'detail-desc' in html:
                    print(f"   ✓ 包含正文")
                if '关注' in child.text:
                    print(f"   ⚠️  包含关注按钮")
                    
    finally:
        page.quit()

if __name__ == "__main__":
    analyze_xhs_structure()
