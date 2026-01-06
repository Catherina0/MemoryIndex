#!/usr/bin/env python3
"""
全功能自检和测试脚本
检查系统所有组件是否正常工作
"""

import sys
import subprocess
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
    required = ['groq', 'paddleocr', 'tabulate']
    for dep in required:
        try:
            __import__(dep)
            print(f"   ✅ {dep}")
        except ImportError:
            print(f"   ❌ {dep} 未安装")
            errors.append(dep)
    
    # dotenv 特殊处理
    try:
        import dotenv
        print("   ✅ python-dotenv")
    except ImportError:
        print("   ❌ python-dotenv 未安装")
        errors.append('python-dotenv')
    
    # 可选依赖 - 搜索
    try:
        import whoosh
        print("   ✅ whoosh")
    except ImportError:
        print("   ⚠️  whoosh 未安装（可选，用于中文搜索）")
    
    try:
        import jieba
        print("   ✅ jieba")
    except ImportError:
        print("   ⚠️  jieba 未安装（可选，用于中文分词）")
    
    # 可选依赖 - 网页归档
    try:
        import crawl4ai
        print("   ✅ crawl4ai（归档）")
    except ImportError:
        print("   ⚠️  crawl4ai 未安装（网页归档需要）")
    
    try:
        import playwright
        print("   ✅ playwright（归档）")
    except ImportError:
        print("   ⚠️  playwright 未安装（网页归档需要）")
    
    try:
        import bs4
        print("   ✅ beautifulsoup4（归档）")
    except ImportError:
        print("   ⚠️  beautifulsoup4 未安装（网页归档需要）")
    
    try:
        import html2text
        print("   ✅ html2text（归档）")
    except ImportError:
        print("   ⚠️  html2text 未安装（网页归档需要）")
    
    try:
        import browser_cookie3
        print("   ✅ browser-cookie3（Cookie管理）")
    except ImportError:
        print("   ⚠️  browser-cookie3 未安装（可选，用于浏览器Cookie）")
    
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
    
    try:
        from archiver.utils.cookie_manager import (
            CookieManager, 
            get_xiaohongshu_cookies
        )
        
        print("   ✅ Cookie管理器导入成功")
        
        # 创建管理器
        manager = CookieManager()
        print("   ✅ CookieManager 初始化成功")
        
        # 检查XHS配置
        config_path = Path("XHS-Downloader") / "Volume" / "settings.json"
        if config_path.exists():
            import json
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            has_cookie = bool(config.get('cookie'))
            has_ua = bool(config.get('user_agent'))
            
            print(f"   {'✅' if has_cookie else '⚠️ '} 小红书Cookie: {'已配置' if has_cookie else '未配置'}")
            print(f"   {'✅' if has_ua else '⚠️ '} User-Agent: {'已配置' if has_ua else '未配置'}")
            
            # 测试Cookie加载
            cookies = get_xiaohongshu_cookies()
            if cookies:
                print(f"   ✅ Cookie加载成功 ({len(cookies)} 个字段)")
                
                # 检查关键字段
                if 'web_session' in cookies:
                    print("   ✅ 包含 web_session 字段")
                else:
                    print("   ⚠️  缺少 web_session 字段")
            else:
                print("   ⚠️  Cookie加载失败")
        else:
            print("   ⚠️  XHS-Downloader 配置不存在")
            print("      运行 make config-xhs-cookie 配置")
        
        # 测试从XHS配置加载
        xhs_cookies = manager.load_from_xhs_config()
        if xhs_cookies:
            print(f"   ✅ XHS配置加载功能正常")
        else:
            print(f"   ⚠️  XHS配置未设置（可选）")
        
    except Exception as e:
        print(f"   ❌ Cookie管理检查失败: {e}")
        return ['cookie-management']
    
    return []


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
        
        if 'database' in all_errors:
            print("   • 数据库问题:")
            print("     - 初始化: make db-init")
        
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
