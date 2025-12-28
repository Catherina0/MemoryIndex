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
    
    # 可选依赖
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
    
    # 总结
    print("\n" + "━" * 50)
    if all_errors:
        print(f"⚠️  发现 {len(all_errors)} 个问题:")
        for err in all_errors:
            print(f"   • {err}")
        print("\n请修复以上问题后重新运行 make selftest")
        print("━" * 50)
        return 1
    else:
        print("✅ 所有检查通过！系统运行正常")
        print("━" * 50)
        return 0


if __name__ == '__main__':
    sys.exit(main())
