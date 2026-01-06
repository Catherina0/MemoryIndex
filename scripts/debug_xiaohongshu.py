#!/usr/bin/env python3
"""
小红书页面结构调试脚本
"""

from DrissionPage import ChromiumPage, ChromiumOptions
import time


def debug_xiaohongshu_page():
    """调试小红书页面结构"""
    url = "https://www.xiaohongshu.com/discovery/item/6958dc6f000000002203209f"
    
    # 配置浏览器
    co = ChromiumOptions()
    co.set_argument('--headless=new')
    co.set_user_agent('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
    co.set_argument('--disable-blink-features=AutomationControlled')
    co.set_paths(browser_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
    
    page = ChromiumPage(co)
    
    try:
        print("🌐 正在访问小红书...")
        page.get(url)
        
        # 等待页面加载
        page.wait.load_start()
        time.sleep(3)
        
        # 滚动加载
        print("📜 滚动页面...")
        page.scroll.to_bottom()
        time.sleep(1)
        
        print(f"\n📄 页面标题: {page.title}\n")
        
        # 测试各种选择器
        selectors = [
            "#detail-desc",
            ".note-content", 
            ".content",
            "[class*='noteContainer']",
            "[class*='content']",
            "article",
            "main",
            "#app",
            ".container"
        ]
        
        print("🔍 测试选择器：")
        print("=" * 60)
        
        for selector in selectors:
            element = page.ele(selector, timeout=1)
            if element:
                text = element.text.strip()
                html_len = len(element.html)
                print(f"✓ {selector:30s} | 文本: {len(text):4d} 字符 | HTML: {html_len:6d} 字节")
                if text:
                    print(f"  内容预览: {text[:100]}...")
            else:
                print(f"✗ {selector:30s} | 未找到")
        
        print("\n" + "=" * 60)
        
        # 查找所有可能包含内容的元素
        print("\n🔍 查找所有包含文本的主要元素：")
        print("=" * 60)
        
        # 尝试找所有 div
        divs = page.eles('tag:div')
        content_divs = []
        
        for div in divs[:50]:  # 只检查前50个
            text = div.text.strip()
            if len(text) > 100:  # 内容足够长
                classes = div.attr('class') or ''
                content_divs.append({
                    'classes': classes,
                    'text_length': len(text),
                    'preview': text[:80]
                })
        
        # 按文本长度排序
        content_divs.sort(key=lambda x: x['text_length'], reverse=True)
        
        print(f"发现 {len(content_divs)} 个可能的内容容器：\n")
        for i, div in enumerate(content_divs[:5], 1):
            print(f"{i}. class=\"{div['classes'][:50]}...\"")
            print(f"   长度: {div['text_length']} 字符")
            print(f"   预览: {div['preview']}...\n")
        
        # 保存完整HTML用于分析
        with open('/tmp/xiaohongshu_debug.html', 'w', encoding='utf-8') as f:
            f.write(page.html)
        print(f"✓ 完整HTML已保存到: /tmp/xiaohongshu_debug.html")
        
    finally:
        page.quit()
        print("\n✓ 浏览器已关闭")


if __name__ == '__main__':
    debug_xiaohongshu_page()
