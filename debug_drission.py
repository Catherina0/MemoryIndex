from DrissionPage import ChromiumOptions

try:
    co = ChromiumOptions()
    print("Methods in ChromiumOptions:")
    for attr in dir(co):
        if 'headless' in attr:
            print(f" - {attr}")
except Exception as e:
    print(f"Error: {e}")
