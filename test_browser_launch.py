from archiver.utils.browser_manager import BrowserManager
import logging
import time

logging.basicConfig(level=logging.INFO)

def test_launch():
    bm = BrowserManager()
    try:
        # Try with headless=False, relying on LSUIElement for invisibility
        browser = bm.get_browser(headless=False) 
        print("Browser launched successfully!")
        
        tab = bm.new_tab("https://example.com")
        print(f"Title: {tab.title}")
        
        time.sleep(2)
    except Exception as e:
        print(f"FAILED: {e}")
    finally:
        bm.cleanup()

if __name__ == "__main__":
    test_launch()
