import sys
sys.path.insert(0, '.')

from DrissionPage import ChromiumPage, ChromiumOptions
import time

options = ChromiumOptions()
options.set_user_data_path("./browser_data")
options.headless(True)

page = ChromiumPage(addr_or_opts=options)

url = "https://x.com/LiangyueX/status/2006259129070018882"
print(f"访问: {url}")
page.get(url)
time.sleep(3)

# 尝试不同的选择器
selectors = [
    "article[data-testid='tweet']",
    "[data-testid='tweetText']",
    "article",
    "[data-testid='tweet']"
]

for sel in selectors:
    print(f"\n{'='*60}")
    print(f"测试选择器: {sel}")
    print('='*60)
    elements = page.eles(sel)
    print(f"找到 {len(elements)} 个元素")
    if elements:
        elem = elements[0]
        text = elem.text
        print(f"文本长度: {len(text)} 字符")
        print(f"HTML长度: {len(elem.html)} 字符")
        if text:
            print(f"文本预览 (前500字符):")
            print(text[:500])

page.quit()
