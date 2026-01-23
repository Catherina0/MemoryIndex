"""
CookieManager
Handles website authentication states using multiple sources:
1. cookies.txt (Netscape format) - Preferred/Resilient
2. Browser local database (via browser_cookie3) - Fallback/Fragile
3. Platform-specific JSON configs (Legacy support for XHS/Zhihu)
"""

import json
import logging
from typing import Dict, Optional
from pathlib import Path

try:
    import browser_cookie3
    BROWSER_COOKIE3_AVAILABLE = True
except ImportError:
    BROWSER_COOKIE3_AVAILABLE = False
    # No warning here, as it's not strictly required if cookies.txt is used

try:
    from core.config import cfg
except ImportError:
    # Fallback for standalone usage
    cfg = None

logger = logging.getLogger(__name__)


class CookieManager:
    """Cookie/Authentication Manager"""
    
    def __init__(self):
        self.cookies_cache = {}
    
    def load_from_browser(
        self,
        domain: str,
        browser: str = 'chrome'
    ) -> Optional[Dict[str, str]]:
        """
        Load cookies with the following priority:
        1. Configured cookies.txt (cfg.cookies_file_path)
        2. Local browser database (browser_cookie3)
        
        Args:
            domain: Target domain
            browser: Browser type for DB lookup (chrome, firefox, edge, safari)
        
        Returns:
            Cookie dictionary or None
        """
        # --- Strategy 1: Load from cookies.txt (Robust) ---
        if cfg and cfg.cookies_file_path:
            logger.debug(f"Checking configured cookies file: {cfg.cookies_file_path}")
            file_cookies = self.load_from_file(str(cfg.cookies_file_path))
            if file_cookies:
                # Basic filtering for domain could be added here if needed
                return file_cookies

        # --- Strategy 2: Browser DB (Fragile) ---
        if not BROWSER_COOKIE3_AVAILABLE:
            if not cfg or not cfg.cookies_file_path:
                 logger.debug("browser_cookie3 not installed and no cookies.txt configured.")
            return None
        
        # Check cache
        cache_key = f"{browser}:{domain}"
        if cache_key in self.cookies_cache:
            logger.debug(f"Using cached cookies for {domain}")
            return self.cookies_cache[cache_key]
        
        try:
            logger.info(f"Attempting to load cookies from {browser} for {domain}...")
            if browser.lower() == 'chrome':
                cj = browser_cookie3.chrome(domain_name=domain)
            elif browser.lower() == 'firefox':
                cj = browser_cookie3.firefox(domain_name=domain)
            elif browser.lower() == 'edge':
                cj = browser_cookie3.edge(domain_name=domain)
            elif browser.lower() == 'safari':
                cj = browser_cookie3.safari(domain_name=domain)
            else:
                logger.error(f"Unsupported browser: {browser}")
                return None
            
            cookies_dict = {cookie.name: cookie.value for cookie in cj}
            self.cookies_cache[cache_key] = cookies_dict
            
            logger.info(f"Loaded {len(cookies_dict)} cookies for {domain} from {browser}")
            return cookies_dict
            
        except Exception as e:
            logger.warning(f"Failed to load cookies from browser DB: {e}")
            logger.info("Tip: Try exporting cookies to 'cookies.txt' in project root.")
            return None
    
    def load_from_file(self, cookie_file: str) -> Optional[Dict[str, str]]:
        """
        Load cookies from Netscape format file
        """
        path = Path(cookie_file)
        if not path.exists():
            return None

        try:
            cookies_dict = {}
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    parts = line.split('\t')
                    if len(parts) >= 7:
                        name = parts[5]
                        value = parts[6]
                        cookies_dict[name] = value
            
            if cookies_dict:
                logger.info(f"Loaded {len(cookies_dict)} cookies from {path.name}")
                return cookies_dict
            return None
            
        except Exception as e:
            logger.error(f"Failed to load cookies from file {cookie_file}: {e}")
            return None

    # --- Legacy / Platform Specific Loaders ---
    
    def load_from_xhs_config(self) -> Optional[Dict[str, str]]:
        """Legacy: Load from XHS specific JSON"""
        # Try new unified config first
        if cfg:
             pass
             
        try:
            unified_path = Path(__file__).parent.parent / "config" / "xiaohongshu_cookie.json"
            if unified_path.exists():
                 return self._load_json_cookie(unified_path)
                 
            legacy_path = Path(__file__).parent.parent.parent / "XHS-Downloader" / "Volume" / "settings.json"
            if legacy_path.exists():
                return self._load_json_cookie(legacy_path)
                
            return None
        except Exception:
            return None

    def _load_json_cookie(self, path: Path) -> Optional[Dict[str, str]]:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            cookie_str = data.get('cookie', '')
            if not cookie_str: return None
            
            cookies = {}
            for item in cookie_str.split(';'):
                if '=' in item:
                    k, v = item.split('=', 1)
                    cookies[k.strip()] = v.strip()
            return cookies
        except Exception:
            return None

    def load_from_zhihu_config(self) -> Optional[Dict[str, str]]:
        """Legacy: Load from Zhihu specific JSON"""
        try:
            config_path = Path(__file__).parent.parent / "config" / "zhihu_cookie.json"
            if not config_path.exists(): return None
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            if config.get('use_browser', False): return None
            
            cookie_str = config.get('cookie', '')
            if not cookie_str: return None
            
            cookies_dict = {}
            for item in cookie_str.split(';'):
                item = item.strip()
                if '=' in item:
                    key, value = item.split('=', 1)
                    cookies_dict[key.strip()] = value.strip()
            return cookies_dict
        except Exception:
            return None
    
    def save_to_xhs_config(self, cookie: str) -> bool:
         """Legacy: Save to XHS config"""
         return False # Disabled in this version to encourage new workflow


def get_cookies_for_domain(domain: str, browser: str = 'chrome') -> Optional[Dict[str, str]]:
    """Helper function to get cookies"""
    manager = CookieManager()
    return manager.load_from_browser(domain, browser)
