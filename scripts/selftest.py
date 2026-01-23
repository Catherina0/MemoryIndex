#!/usr/bin/env python3
"""
全功能自检和测试脚本
检查系统所有组件是否正常工作
"""

import sys
import subprocess
import json
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def print_header(title: str):
    """打印标题"""
    print(f"\n{'─' * 40}")
    print(f"  {title}")
    print(f"{'─' * 40}")


def check_module_imports():
    """1. 核心模块导入测试"""
    print_header("📦 1. 核心模块导入测试")
    
    modules = [
        ('db.models', ['SourceType', 'ProcessingStatus', 'ArtifactType', 'SearchResult']),
        ('db.schema', ['get_connection', 'init_database']),
        ('db.repository', ['VideoRepository']),
        ('db.search', ['SearchRepository']),
        ('db.whoosh_search', ['WhooshSearchIndex', 'check_whoosh_status']),
        ('core.video_downloader', ['VideoDownloader']),
        ('core.process_video', ['process_video']),
        ('archiver', ['UniversalArchiver', 'detect_platform']),
        ('archiver.utils.cookie_manager', ['CookieManager', 'get_xiaohongshu_cookies']),
        ('archiver.platforms', ['ZhihuAdapter', 'XiaohongshuAdapter', 'BilibiliAdapter']),
    ]
    
    errors = []
    for mod_name, items in modules:
        try:
            mod = __import__(mod_name, fromlist=items)
            for item in items:
                getattr(mod, item)
            print(f"   ✅ {mod_name}")
        except Exception as e:
            print(f"   ❌ {mod_name}: {e}")
            errors.append(mod_name)
    
    return errors


def check_dependencies():
    """2. 依赖库检查"""
    print_header("🔧 2. 依赖库检查")
    
    errors = []
    
    # 必需依赖
    required = [
        ('numpy', '数据处理'),
        ('groq', 'Groq API'),
        ('dotenv', '环境变量'),
        ('tqdm', '进度条'),
        ('tabulate', '表格输出'),
    ]
    for dep, desc in required:
        try:
            if dep == 'dotenv':
                __import__('dotenv')
            else:
                __import__(dep)
            print(f"   ✅ {dep} ({desc})")
        except ImportError:
            print(f"   ❌ {dep} ({desc}) 未安装")
            errors.append(dep)
    
    # Gemini API（可选，用于超长文本）
    try:
        from google import genai
        print("   ✅ google-genai（可选，长文本处理）")
    except ImportError:
        print("   ⚠️  google-genai 未安装（可选，用于处理超过 13 万 token 的长文本）")
        print("      安装: pip install google-genai")
    
    # 视频下载
    try:
        import yt_dlp
        print("   ✅ yt-dlp（视频下载）")
    except ImportError:
        print("   ⚠️  yt-dlp 未安装（视频下载功能将不可用）")
        print("      安装: pip install yt-dlp")
    
    # 全文搜索
    try:
        import whoosh
        print("   ✅ Whoosh（全文搜索引擎）")
    except ImportError:
        print("   ⚠️  Whoosh 未安装（搜索功能将不可用）")
        print("      安装: pip install Whoosh")
    
    try:
        import jieba
        print("   ✅ jieba（中文分词）")
    except ImportError:
        print("   ⚠️  jieba 未安装（中文搜索将受影响）")
        print("      安装: pip install jieba")
    
    # 网页归档
    try:
        import crawl4ai
        print("   ✅ crawl4ai（网页爬虫）")
    except ImportError:
        print("   ⚠️  crawl4ai 未安装（网页归档功能将不可用）")
        print("      安装: pip install crawl4ai")
    
    try:
        import playwright
        print("   ✅ playwright（浏览器自动化）")
    except ImportError:
        print("   ⚠️  playwright 未安装（部分网页归档功能将不可用）")
        print("      安装: pip install playwright && playwright install")
    
    try:
        import bs4
        print("   ✅ beautifulsoup4（HTML解析）")
    except ImportError:
        print("   ⚠️  beautifulsoup4 未安装（HTML解析功能将不可用）")
        print("      安装: pip install beautifulsoup4")
    
    try:
        import html2text
        print("   ✅ html2text（HTML转Markdown）")
    except ImportError:
        print("   ⚠️  html2text 未安装（HTML转换功能将不可用）")
        print("      安装: pip install html2text")
    
    # 小红书相关（可选）
    try:
        import httpx
        print("   ✅ httpx（HTTP客户端，小红书下载需要）")
    except ImportError:
        print("   ⚠️  httpx 未安装（小红书下载功能将不可用）")
    
    # OCR 引擎（至少需要一个）
    ocr_available = False
    try:
        import paddleocr
        print("   ✅ paddleocr（可选 OCR 引擎）")
        ocr_available = True
    except ImportError:
        print("   ⚠️  paddleocr 未安装（可选，跨平台 OCR）")
    
    # Vision OCR (macOS 系统自带)
    import platform
    if platform.system() == 'Darwin':
        try:
            result = subprocess.run(['swift', '--version'], capture_output=True, timeout=2)
            if result.returncode == 0:
                print("   ✅ Apple Vision OCR（系统自带）")
                ocr_available = True
            else:
                print("   ⚠️  Swift 不可用")
        except:
            print("   ⚠️  Swift 不可用")
    
    if not ocr_available:
        print("   ⚠️  未找到可用的 OCR 引擎")
        print("      macOS: 应自动使用 Vision OCR")
        print("      其他平台: 运行 'make install-paddle-ocr'")
    
    return errors


def check_database():
    """3. 数据库状态"""
    print_header("🗄️  3. 数据库状态")
    
    errors = []
    try:
        from db.schema import check_database_health
        stats = check_database_health()
        
        print(f"   📊 视频数: {stats.get('videos', 0)}")
        print(f"   📊 产物数: {stats.get('artifacts', 0)}")
        print(f"   📊 标签数: {stats.get('tags', 0)}")
        print(f"   📊 FTS索引: {stats.get('fts_content', 0)} 条")
        print(f"   💾 数据库大小: {stats.get('db_size_mb', 0):.2f} MB")
    except Exception as e:
        print(f"   ❌ 数据库检查失败: {e}")
        errors.append('database')
    
    return errors


def check_whoosh():
    """4. Whoosh 搜索引擎"""
    print_header("🔍 4. Whoosh 搜索引擎")
    
    try:
        from db.whoosh_search import check_whoosh_status, get_whoosh_index
        status = check_whoosh_status()
        
        print(f"   Whoosh 安装: {'✅' if status['whoosh_installed'] else '❌'}")
        print(f"   jieba 安装: {'✅' if status['jieba_installed'] else '❌'}")
        
        if status['ready']:
            idx = get_whoosh_index()
            st = idx.get_stats()
            print(f"   索引文档数: {st.get('doc_count', 0)}")
            print(f"   索引目录: {st.get('index_dir', 'N/A')}")
    except Exception as e:
        print(f"   ⚠️  Whoosh 检查跳过: {e}")
    
    return []


def check_search():
    """5. 搜索功能测试"""
    print_header("🔎 5. 搜索功能测试")
    
    errors = []
    try:
        from db.search import SearchRepository
        repo = SearchRepository()
        
        # 测试英文搜索 (FTS)
        r1 = repo.search('test', limit=1)
        print(f"   ✅ FTS搜索正常 (英文) - 找到 {len(r1)} 条")
        
        # 测试中文搜索 (Whoosh)
        r2 = repo.search('测试', limit=1)
        print(f"   ✅ Whoosh搜索正常 (中文) - 找到 {len(r2)} 条")
        
    except Exception as e:
        print(f"   ❌ 搜索测试失败: {e}")
        errors.append('search')
    
    return errors


def check_downloader():
    """6. 下载器状态"""
    print_header("⬇️  6. 下载器状态")
    
    try:
        from core.video_downloader import VideoDownloader
        dl = VideoDownloader()
        
        print(f"   yt-dlp: {'✅ ' + dl.ytdlp_path if dl.ytdlp_path else '❌ 未安装'}")
        print(f"   BBDown: {'✅ ' + dl.bbdown_path if dl.bbdown_path else '⚠️  未安装（B站备用）'}")
    except Exception as e:
        print(f"   ❌ 下载器检查失败: {e}")
    
    return []


def check_ffmpeg():
    """7. FFmpeg 检查"""
    print_header("🎬 7. FFmpeg 检查")
    
    errors = []
    try:
        result = subprocess.run(
            ['ffmpeg', '-version'], 
            capture_output=True, 
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            version = result.stdout.split('\n')[0]
            print(f"   ✅ {version[:60]}...")
        else:
            print("   ❌ ffmpeg 运行异常")
            errors.append('ffmpeg')
    except FileNotFoundError:
        print("   ❌ ffmpeg 未安装")
        print("      安装方法: brew install ffmpeg")
        errors.append('ffmpeg')
    except Exception as e:
        print(f"   ❌ ffmpeg 检查失败: {e}")
        errors.append('ffmpeg')
    
    return errors


def check_ocr_engines():
    """7.5 OCR 引擎检查"""
    print_header("🔍 7.5. OCR 引擎检查")
    
    import platform
    errors = []
    ocr_engines = []
    
    # 1. 检查 Vision OCR（macOS）
    if platform.system() == 'Darwin':
        print("   🍎 Apple Vision OCR (macOS 原生):")
        
        # 检查 macOS 版本
        try:
            mac_ver = platform.mac_ver()[0]
            major_ver = int(mac_ver.split('.')[0]) if mac_ver else 0
            if major_ver >= 10:
                print(f"      ✅ macOS 版本: {mac_ver}")
            else:
                print(f"      ❌ macOS 版本过低: {mac_ver} (需要 10.15+)")
                errors.append('vision-ocr-version')
        except:
            print("      ⚠️  无法检测 macOS 版本")
        
        # 检查 Swift
        try:
            result = subprocess.run(
                ['swift', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                swift_ver = result.stdout.split('\n')[0]
                print(f"      ✅ Swift: {swift_ver[:50]}")
                
                # 检查 Swift 脚本
                swift_script = Path('ocr/vision_ocr.swift')
                if swift_script.exists():
                    print(f"      ✅ Swift OCR 脚本: {swift_script}")
                    ocr_engines.append('vision')
                else:
                    print(f"      ❌ Swift OCR 脚本不存在: {swift_script}")
                    errors.append('vision-ocr-script')
            else:
                print("      ❌ Swift 不可用")
                errors.append('vision-ocr-swift')
        except FileNotFoundError:
            print("      ❌ Swift 未安装（系统应自带）")
            errors.append('vision-ocr-swift')
        except Exception as e:
            print(f"      ⚠️  Swift 检查失败: {e}")
        
        # 测试 Vision OCR Python 接口
        try:
            from ocr.ocr_vision import init_vision_ocr
            print("      ✅ Vision OCR Python 模块")
        except ImportError as e:
            print(f"      ⚠️  Vision OCR Python 模块导入失败: {e}")
    else:
        print(f"   ⚠️  非 macOS 系统 ({platform.system()})，Vision OCR 不可用")
    
    print()
    
    # 2. 检查 PaddleOCR（跨平台）
    print("   🐼 PaddleOCR (跨平台):")
    try:
        import paddleocr
        print("      ✅ PaddleOCR 已安装")
        
        # 检查 Paddle
        try:
            import paddle
            paddle_ver = paddle.__version__
            print(f"      ✅ PaddlePaddle: {paddle_ver}")
            
            # 检查 GPU 支持
            if paddle.is_compiled_with_cuda():
                print("      ✅ GPU 支持: 可用")
            else:
                print("      ℹ️  GPU 支持: 不可用（使用 CPU）")
            
            ocr_engines.append('paddle')
            
        except Exception as e:
            print(f"      ⚠️  Paddle 检查失败: {e}")
        
        # 检查 OCR 工具模块
        try:
            from ocr.ocr_utils import init_ocr
            print("      ✅ OCR 工具模块")
        except ImportError as e:
            print(f"      ⚠️  OCR 工具模块导入失败: {e}")
            
    except ImportError:
        print("      ⚠️  PaddleOCR 未安装")
        print("      安装方法: make install-paddle-ocr")
    
    print()
    
    # 3. 总结
    if ocr_engines:
        print(f"   ✅ 可用的 OCR 引擎: {', '.join(ocr_engines)}")
        if 'vision' in ocr_engines:
            print("   💡 推荐: 使用 Vision OCR (macOS 原生，速度快)")
    else:
        print("   ❌ 未找到可用的 OCR 引擎")
        if platform.system() == 'Darwin':
            print("   💡 macOS 用户: 应自动使用 Vision OCR，请检查 Swift 环境")
        else:
            print("   💡 请安装 PaddleOCR: make install-paddle-ocr")
        errors.append('no-ocr-engine')
    
    return errors


def check_api_config():
    """8. API 配置"""
    print_header("🔑 8. API 配置检查")
    
    env_file = Path('.env')
    
    if env_file.exists():
        content = env_file.read_text()
        
        # 检查 GROQ_API_KEY
        if 'GROQ_API_KEY' in content:
            # 排除占位符
            lines = [l for l in content.split('\n') if 'GROQ_API_KEY' in l and not l.strip().startswith('#')]
            if lines:
                value = lines[0].split('=', 1)[1].strip() if '=' in lines[0] else ''
                if value and 'your' not in value.lower() and value != '':
                    print("   ✅ GROQ_API_KEY 已配置")
                else:
                    print("   ⚠️  GROQ_API_KEY 未设置或为占位符")
            else:
                print("   ⚠️  GROQ_API_KEY 被注释")
        else:
            print("   ⚠️  GROQ_API_KEY 未配置")
        
        # 检查 GEMINI_API_KEY
        if 'GEMINI_API_KEY' in content:
            lines = [l for l in content.split('\n') if 'GEMINI_API_KEY' in l and not l.strip().startswith('#')]
            if lines:
                value = lines[0].split('=', 1)[1].strip() if '=' in lines[0] else ''
                if value and 'your' not in value.lower() and value != '':
                    print("   ✅ GEMINI_API_KEY 已配置（用于超长文本处理）")
                else:
                    print("   ⚠️  GEMINI_API_KEY 未设置或为占位符（可选，仅处理超长文本时需要）")
            else:
                print("   ⚠️  GEMINI_API_KEY 被注释（可选）")
        else:
            print("   ℹ️  GEMINI_API_KEY 未配置（可选，仅在处理超过 13 万 token 的长文本时需要）")
    else:
        print("   ❌ .env 文件不存在")
        print("      请复制 config_example.py 创建 .env 文件")
    
    return []


def check_disk_space():
    """9. 磁盘空间检查"""
    print_header("💾 9. 磁盘空间检查")
    
    import shutil
    
    # 检查当前目录磁盘空间
    total, used, free = shutil.disk_usage('.')
    free_gb = free / (1024 ** 3)
    
    if free_gb < 1:
        print(f"   ⚠️  磁盘空间不足: {free_gb:.1f} GB 可用")
    elif free_gb < 5:
        print(f"   ⚠️  磁盘空间较低: {free_gb:.1f} GB 可用")
    else:
        print(f"   ✅ 磁盘空间充足: {free_gb:.1f} GB 可用")
    
    # 检查输出目录大小
    output_dir = Path('output')
    if output_dir.exists():
        total_size = sum(f.stat().st_size for f in output_dir.rglob('*') if f.is_file())
        print(f"   📁 output/ 目录: {total_size / (1024**2):.1f} MB")
    
    videos_dir = Path('videos')
    if videos_dir.exists():
        total_size = sum(f.stat().st_size for f in videos_dir.rglob('*') if f.is_file())
        print(f"   📁 videos/ 目录: {total_size / (1024**2):.1f} MB")
    
    return []


def check_archiver():
    """10. 网页归档功能"""
    print_header("🌐 10. 网页归档功能")
    
    errors = []
    try:
        # 导入测试
        from archiver import UniversalArchiver, detect_platform
        from archiver.utils.url_parser import normalize_url, is_valid_url
        from archiver.platforms import (
            ZhihuAdapter, XiaohongshuAdapter, BilibiliAdapter,
            RedditAdapter, WordPressAdapter
        )
        
        print("   ✅ 归档模块导入成功")
        
        # 平台检测测试
        test_cases = [
            ("https://www.zhihu.com/question/123", "zhihu"),
            ("https://www.xiaohongshu.com/explore/abc", "xiaohongshu"),
            ("https://www.bilibili.com/video/BV123", "bilibili"),
            ("https://www.reddit.com/r/python/", "reddit"),
        ]
        
        platform_ok = True
        for url, expected in test_cases:
            result = detect_platform(url)
            if result == expected:
                print(f"   ✅ 平台检测: {expected}")
            else:
                print(f"   ❌ 平台检测失败: {url} → {result} (应为 {expected})")
                platform_ok = False
        
        if not platform_ok:
            errors.append('archiver-platform-detection')
        
        # 适配器测试
        adapters = [
            (ZhihuAdapter(), "zhihu"),
            (XiaohongshuAdapter(), "xiaohongshu"),
            (BilibiliAdapter(), "bilibili"),
            (RedditAdapter(), "reddit"),
            (WordPressAdapter(), "wordpress"),
        ]
        
        for adapter, name in adapters:
            if adapter.name == name and adapter.content_selector:
                print(f"   ✅ {name} 适配器配置正常")
            else:
                print(f"   ❌ {name} 适配器配置异常")
                errors.append(f'archiver-{name}')
        
        # URL工具测试
        assert normalize_url("example.com") == "https://example.com"
        assert is_valid_url("https://example.com") == True
        print("   ✅ URL工具函数正常")
        
        # 检查归档输出目录
        archived_dir = Path('archived')
        if archived_dir.exists():
            count = len(list(archived_dir.glob('*.md')))
            print(f"   📁 已归档文件: {count} 个")
        
    except Exception as e:
        print(f"   ❌ 归档功能检查失败: {e}")
        errors.append('archiver')
    
    return errors


def check_cookie_management():
    """11. Cookie统一管理"""
    print_header("🍪 11. Cookie统一管理")
    
    errors = []
    configured_platforms = []
    
    try:
        from archiver.utils.cookie_manager import (
            CookieManager, 
            get_xiaohongshu_cookies
        )
        
        print("   ✅ Cookie管理器导入成功")
        
        # 创建管理器
        manager = CookieManager()
        print("   ✅ CookieManager 初始化成功")
        print()
        
        # ========== 检查各平台 Cookie 配置状态 ==========
        print("   📋 平台 Cookie 配置状态:")
        print()
        
        # 1. 小红书 (XHS-Downloader)
        print("   🔴 小红书 (XiaohongShu):")
        
        # 检查统一位置（优先）
        unified_config = Path("archiver") / "config" / "xiaohongshu_cookie.json"
        xhs_config = Path("XHS-Downloader") / "Volume" / "settings.json"
        
        has_cookie = False
        cookie_source = None
        
        # 优先检查统一位置
        if unified_config.exists():
            try:
                with open(unified_config, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                cookie = config.get('cookie', '')
                if cookie:
                    has_cookie = True
                    cookie_source = "unified"
                    print(f"      ✅ Cookie: 已配置 (统一位置)")
                    print(f"         📁 archiver/config/xiaohongshu_cookie.json")
                    print(f"         📊 {len(cookie)} 字符")
                    configured_platforms.append('xiaohongshu')
                    
                    # 测试Cookie加载
                    cookies = get_xiaohongshu_cookies()
                    if cookies:
                        cookie_count = len(cookies)
                        print(f"      ✅ 加载成功: {cookie_count} 个字段")
                        
                        # 检查关键字段
                        if 'web_session' in cookies:
                            print("      ✅ web_session: 已包含")
                        else:
                            print("      ⚠️  web_session: 缺失")
                    else:
                        print("      ⚠️  Cookie加载失败")
            except Exception as e:
                print(f"      ⚠️  统一位置配置读取失败: {e}")
        
        # 检查旧位置（XHS-Downloader）
        if not has_cookie and xhs_config.exists():
            try:
                with open(xhs_config, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                cookie = config.get('cookie', '')
                if cookie:
                    has_cookie = True
                    cookie_source = "legacy"
                    print(f"      ⚠️  Cookie: 使用旧位置（建议迁移）")
                    print(f"         📁 XHS-Downloader/Volume/settings.json")
                    print(f"         📊 {len(cookie)} 字符")
                    print(f"         💡 运行 'make export-cookies' 迁移到统一位置")
                    configured_platforms.append('xiaohongshu')
                    
                    # 测试Cookie加载
                    cookies = get_xiaohongshu_cookies()
                    if cookies:
                        cookie_count = len(cookies)
                        print(f"      ✅ 加载成功: {cookie_count} 个字段")
            except Exception as e:
                print(f"      ⚠️  旧位置配置读取失败: {e}")
        
        if not has_cookie:
            print("      ⚠️  Cookie: 未配置")
            print("      💡 配置方法:")
            print("         1. make config-xhs-cookie (传统方式)")
            print("         2. 手动创建 archiver/config/xiaohongshu_cookie.json (推荐)")
        
        print()
        
        # 2. 知乎 (Zhihu)
        print("   🔵 知乎 (Zhihu):")
        zhihu_config = Path("archiver") / "config" / "zhihu_cookie.json"
        if zhihu_config.exists():
            try:
                with open(zhihu_config, 'r', encoding='utf-8') as f:
                    zhihu_data = json.load(f)
                    zhihu_cookie = zhihu_data.get('cookie', '')
                if zhihu_cookie and len(zhihu_cookie) > 50:  # 检查 cookie 字符串
                    print(f"      ✅ Cookie: 已配置 ({len(zhihu_cookie)} 字符)")
                    configured_platforms.append('zhihu')
                else:
                    print("      ⚠️  Cookie: 已创建但为空")
                    print("      💡 配置方法: make config-zhihu-cookie")
            except Exception as e:
                print(f"      ⚠️  配置读取失败: {e}")
        else:
            print("      ℹ️  Cookie: 未配置（可选，无需登录可访问部分内容）")
            print("      💡 配置方法: make config-zhihu-cookie")
        print()
        
        # 3. B站 (Bilibili)
        print("   🩷 B站 (Bilibili):")
        bilibili_config = Path("archiver") / "config" / "bilibili_cookies.json"
        if bilibili_config.exists():
            try:
                with open(bilibili_config, 'r', encoding='utf-8') as f:
                    bilibili_cookies = json.load(f)
                if bilibili_cookies and len(bilibili_cookies) > 0:
                    print(f"      ✅ Cookie: 已配置 ({len(bilibili_cookies)} 个字段)")
                    configured_platforms.append('bilibili')
                else:
                    print("      ⚠️  Cookie: 已创建但为空")
            except Exception as e:
                print(f"      ⚠️  配置读取失败: {e}")
        else:
            print("      ℹ️  Cookie: 未配置（可选，无需登录可访问部分内容）")
            print("      💡 通过浏览器扩展或手动配置")
        print()
        
        # 4. Reddit
        print("   🟠 Reddit:")
        reddit_config = Path("archiver") / "config" / "reddit_cookies.json"
        if reddit_config.exists():
            try:
                with open(reddit_config, 'r', encoding='utf-8') as f:
                    reddit_cookies = json.load(f)
                if reddit_cookies and len(reddit_cookies) > 0:
                    print(f"      ✅ Cookie: 已配置 ({len(reddit_cookies)} 个字段)")
                    configured_platforms.append('reddit')
                else:
                    print("      ⚠️  Cookie: 已创建但为空")
            except Exception as e:
                print(f"      ⚠️  配置读取失败: {e}")
        else:
            print("      ℹ️  Cookie: 未配置（可选，无需登录可访问公开内容）")
        print()
        
        # 5. 推特/X (Twitter)
        print("   🐦 推特 (Twitter/X):")
        twitter_config = Path("archiver") / "config" / "twitter_cookie.json"
        twitter_browser_data = Path("browser_data") / "Default" / "Cookies"
        
        has_json_config = False
        has_browser_data = False
        
        # 检查 JSON 配置
        if twitter_config.exists():
            try:
                with open(twitter_config, 'r', encoding='utf-8') as f:
                    twitter_data = json.load(f)
                    twitter_cookie = twitter_data.get('cookie', '')
                if twitter_cookie and len(twitter_cookie) > 50:
                    print(f"      ✅ Cookie(JSON): 已配置 ({len(twitter_cookie)} 字符)")
                    configured_platforms.append('twitter')
                    has_json_config = True
                else:
                    print("      ⚠️  Cookie(JSON): 已创建但为空")
            except Exception as e:
                print(f"      ⚠️  Cookie(JSON): 读取失败 - {e}")
        
        # 检查 DrissionPage browser_data
        if twitter_browser_data.exists():
            try:
                import sqlite3
                conn = sqlite3.connect(str(twitter_browser_data))
                cursor = conn.cursor()
                # 查询推特相关的 cookie
                cursor.execute("SELECT COUNT(*) FROM cookies WHERE host_key LIKE '%twitter.com%' OR host_key LIKE '%x.com%'")
                count = cursor.fetchone()[0]
                conn.close()
                
                if count > 0:
                    print(f"      ✅ Cookie(DrissionPage): 已配置 ({count} 条)")
                    if not has_json_config:
                        configured_platforms.append('twitter')
                    has_browser_data = True
                else:
                    print(f"      ℹ️  Cookie(DrissionPage): 未找到推特相关 cookie")
            except Exception as e:
                print(f"      ℹ️  Cookie(DrissionPage): 检查失败")
        
        # 如果两种都没有
        if not has_json_config and not has_browser_data:
            print("      ℹ️  Cookie: 未配置（推荐配置以访问完整内容）")
            print("      💡 方法1: python scripts/login_twitter.py (DrissionPage)")
            print("      💡 方法2: 手动创建 archiver/config/twitter_cookie.json")
        elif has_browser_data and not has_json_config:
            print("      💡 可选: 导出为 JSON 格式以提高兼容性")
        
        print()
        
        # 扫描其他未知的 cookie 配置
        print("   🔍 扫描其他 Cookie 配置:")
        config_dir = Path("archiver") / "config"
        if config_dir.exists():
            all_cookie_files = list(config_dir.glob("*cookie*.json"))
            known_files = {
                Path("archiver") / "config" / "zhihu_cookie.json",
                Path("archiver") / "config" / "bilibili_cookies.json",
                Path("archiver") / "config" / "bilibili_cookie.json",
                Path("archiver") / "config" / "reddit_cookies.json",
                Path("archiver") / "config" / "reddit_cookie.json",
                Path("archiver") / "config" / "twitter_cookie.json",
                Path("archiver") / "config" / "twitter_cookies.json",
            }
            unknown_files = [f for f in all_cookie_files if f not in known_files]
            
            if unknown_files:
                for unknown_file in unknown_files:
                    print(f"      ⚠️  发现其他配置: {unknown_file.name}")
                    try:
                        with open(unknown_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            cookie = data.get('cookie', '')
                            if cookie and len(cookie) > 50:
                                print(f"         ✅ 已配置 ({len(cookie)} 字符)")
                            else:
                                print(f"         ℹ️  未配置或为空")
                    except:
                        pass
            else:
                print(f"      ✅ 无其他配置文件")
        print()
        
        # 总结
        print("   " + "─" * 50)
        if configured_platforms:
            platform_map = {
                'xiaohongshu': '小红书',
                'zhihu': '知乎', 
                'bilibili': 'B站',
                'reddit': 'Reddit',
                'twitter': '推特'
            }
            platform_names = [platform_map.get(p, p) for p in configured_platforms]
            print(f"   ✅ 已配置平台 ({len(configured_platforms)}): {', '.join(platform_names)}")
        else:
            print("   ⚠️  尚未配置任何平台的 Cookie")
            print("   💡 小红书等平台需要 Cookie 才能正常访问")
        
        print()
        print("   💡 配置优先级:")
        print("      🔴 必需: 小红书（反爬虫严格）- make config-xhs-cookie")
        print("      🟡 推荐: 知乎、推特（增强访问能力）- make config-zhihu-cookie")
        print("      🟢 可选: B站、Reddit（公开内容无需登录）")
        
    except Exception as e:
        print(f"   ❌ Cookie管理检查失败: {e}")
        import traceback
        traceback.print_exc()
        errors.append('cookie-management')
    
    return errors


def check_archiver_integration():
    """12. 归档集成测试"""
    print_header("🔗 12. 归档集成测试")
    
    try:
        # 测试自动Cookie加载
        from archiver.utils.url_parser import detect_platform
        from archiver.utils.cookie_manager import get_xiaohongshu_cookies
        
        # 平台检测
        xhs_url = "https://www.xiaohongshu.com/explore/abc123"
        platform = detect_platform(xhs_url)
        print(f"   ✅ URL平台检测: {platform}")
        
        # Cookie可用性
        if platform == "xiaohongshu":
            cookies = get_xiaohongshu_cookies()
            if cookies:
                print(f"   ✅ 小红书Cookie自动加载可用")
            else:
                print(f"   ⚠️  小红书Cookie未配置（需要时配置）")
        
        # 测试Markdown转换器
        from archiver.core.markdown_converter import MarkdownConverter
        converter = MarkdownConverter()
        
        test_html = "<p>测试<strong>内容</strong></p>"
        markdown = converter.convert(
            html=test_html,
            title="测试",
            url="https://example.com",
            platform="test"
        )
        
        if "title: 测试" in markdown and "测试" in markdown:
            print("   ✅ Markdown转换器正常")
        else:
            print("   ❌ Markdown转换器异常")
            return ['markdown-converter']
        
        # 检查文档
        docs = [
            "docs/ARCHIVER_GUIDE.md",
            "docs/ARCHIVER_QUICKREF.md",
            "docs/COOKIE_UNIFIED.md",
            "archiver/README.md",
        ]
        
        missing_docs = []
        for doc in docs:
            if Path(doc).exists():
                print(f"   ✅ {doc}")
            else:
                print(f"   ❌ {doc} 缺失")
                missing_docs.append(doc)
        
        if missing_docs:
            return ['archiver-docs']
        
    except Exception as e:
        print(f"   ❌ 归档集成测试失败: {e}")
        return ['archiver-integration']
    
    return []


def main():
    """主函数"""
    print("━" * 50)
    print("🔬 全功能自检和测试")
    print("━" * 50)
    
    all_errors = []
    
    # 运行所有检查
    all_errors.extend(check_module_imports())
    all_errors.extend(check_dependencies())
    all_errors.extend(check_database())
    all_errors.extend(check_whoosh())
    all_errors.extend(check_search())
    all_errors.extend(check_downloader())
    all_errors.extend(check_ffmpeg())
    all_errors.extend(check_ocr_engines())  # 新增 OCR 检查
    all_errors.extend(check_api_config())
    all_errors.extend(check_disk_space())
    all_errors.extend(check_archiver())
    all_errors.extend(check_cookie_management())
    all_errors.extend(check_archiver_integration())
    
    # 总结
    print("\n" + "━" * 50)
    if all_errors:
        print(f"⚠️  发现 {len(all_errors)} 个问题:")
        for err in all_errors:
            print(f"   • {err}")
        print("\n💡 建议:")
        
        if 'archiver' in all_errors or any('archiver' in e for e in all_errors):
            print("   • 网页归档功能问题:")
            print("     - 安装依赖: make install")
            print("     - 安装浏览器: playwright install chromium")
            print("     - 运行测试: make test-archiver")
        
        if 'cookie-management' in all_errors:
            print("   • Cookie管理问题:")
            print("     - 配置小红书Cookie: make config-xhs-cookie")
            print("     - 测试Cookie: python scripts/test_cookie_unified.py")
        
        if 'ffmpeg' in all_errors:
            print("   • FFmpeg问题:")
            print("     - 安装: brew install ffmpeg")
        
        if any('ocr' in e for e in all_errors):
            print("   • OCR 引擎问题:")
            print("     - macOS: 检查 Swift 环境 (swift --version)")
            print("     - 跨平台: 安装 PaddleOCR (make install-paddle-ocr)")
            print("     - 测试 Vision OCR: make test-vision-ocr")
        
        if 'database' in all_errors:
            print("   • 数据库问题:")
            print("     - 初始化: memidx init")
        
        print("\n请修复以上问题后重新运行 make selftest")
        print("━" * 50)
        return 1
    else:
        print("✅ 所有检查通过！系统运行正常")
        print("\n🎯 功能状态:")
        print("   ✅ 视频处理系统")
        print("   ✅ 视频下载系统")
        print("   ✅ 数据库与搜索")
        print("   ✅ 网页归档系统")
        print("   ✅ Cookie统一管理")
        print("\n💡 快速开始:")
        print("   • 处理视频: make run VIDEO=video.mp4")
        print("   • 下载视频: make download-run URL=视频链接")
        print("   • 归档网页: make archive URL=网页链接")
        print("   • 搜索内容: make search Q='关键词'")
        print("━" * 50)
        return 0


if __name__ == '__main__':
    sys.exit(main())
