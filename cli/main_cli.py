#!/usr/bin/env python3
"""
MemoryIndex 统一命令行入口
整合所有功能：视频处理、下载、搜索、归档等
"""
import sys
import warnings
import argparse
from pathlib import Path

# 过滤第三方库的已知警告
warnings.filterwarnings('ignore', message='pkg_resources is deprecated')
warnings.filterwarnings('ignore', category=SyntaxWarning, module='whoosh')

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def run_init(args):
    """初始化数据库和环境"""
    print("🚀 初始化 MemoryIndex 环境...")
    
    print("\n[1/3] 初始化 SQLite 数据库...")
    try:
        from db.schema import init_database
        init_database(force_recreate=False)
        print("✅ 数据库已就绪")
    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
        return

    print("\n[2/3] 初始化 Whoosh 索引...")
    try:
        from db.whoosh_search import WhooshSearchIndex
        idx = WhooshSearchIndex()
        idx.init_index()
        print("✅ 搜索索引已就绪")
    except Exception as e:
        print(f"❌ 索引初始化失败: {e}")
        
    print("\n[3/3] 配置 API 环境...")
    if hasattr(args, 'no_api') and args.no_api:
        print("⏭️  跳过 API 配置")
    else:
        # Check for config
        try:
            from core.config import cfg
            cfg.print_summary()
        except ImportError:
            pass
        configure_api()
        
    print("\n✨ 初始化完成！建议运行 'memidx selftest' 验证。")


def main():
    # 智能路由：如果直接传入一个URL，则自动识别为网页或视频
    if len(sys.argv) >= 2 and sys.argv[1].startswith('http'):
        url = sys.argv[1]
        # 简单判定视频平台
        if any(domain in url for domain in ['bilibili.com', 'youtube.com', 'youtu.be', 'v.qq.com']):
            print(f"🤖 智能路由：识别到视频URL，准备下载和处理 -> {url}")
            sys.argv.insert(1, 'download')
            # 默认自动处理并进行OCR
            if '--process' not in sys.argv: sys.argv.append('--process')
            if '--ocr' not in sys.argv: sys.argv.append('--ocr')
        else:
            print(f"🤖 智能路由：识别到网页URL，准备归档 -> {url}")
            sys.argv.insert(1, 'archive')

    # Makefile 桥接路由：无缝继承所有 Makefile 脚本功能
    native_commands = {'init', 'search', 'tags', 'topics', 'list-tags', 'suggest', 'list', 'show', 'delete', 'process', 'download', 'archive', 'selftest', 'config', 'stats', '-h', '--help', '--version'}
    if len(sys.argv) >= 2 and sys.argv[1] not in native_commands and not sys.argv[1].startswith('-'):
        # 如果不是内置命令，且不像是个参数标志，尝试转发给 Makefile
        target = sys.argv[1]
        if (PROJECT_ROOT / "Makefile").exists():
            import subprocess
            print(f"🛠️  未识别的命令，已尝试转发至 Makefile 执行: make {target}")
            try:
                result = subprocess.run(["make", target] + sys.argv[2:], cwd=str(PROJECT_ROOT))
                sys.exit(result.returncode)
            except KeyboardInterrupt:
                sys.exit(130)
            except FileNotFoundError:
                pass


    parser = argparse.ArgumentParser(
        prog='memidx',
        description='MemoryIndex - 智能视频知识库系统',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📹 MemoryIndex - 功能概览
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔍 搜索功能：
  memidx search "机器学习"                    # 全文搜索
  memidx search "人工智能" --field transcript  # 仅在转写中搜索
  memidx tags --tags 教育 科技                # 按标签过滤
  memidx list                                 # 列出所有视频
  memidx show 123                             # 查看视频详情

📹 视频处理：
  memidx process VIDEO.mp4                    # 处理视频（音频+AI总结）
  memidx process VIDEO.mp4 --ocr              # 完整处理（音频+OCR+AI）
  memidx process VIDEO.mp4 --ocr-engine vision # 使用 Vision OCR

📥 下载视频：
  memidx download URL                         # 下载视频
  memidx download URL --process               # 下载后自动处理
  memidx download URL --process --ocr         # 下载后完整处理

🌐 网页归档：
  memidx archive URL                          # 归档网页为 Markdown
  memidx archive URL --output custom.md       # 指定输出文件

�️ 扩展生态 (无缝兼容 Makefile)：
  memidx setup                                # 安装依赖与环境
  memidx db-reset                             # 重建数据库 
  memidx clean-all                            # 清理所有缓存/产物
  (绝大多数 `make <命令>` 现在都可等效替换为 `memidx <命令>`)

�🔧 系统维护：
  memidx selftest                             # 系统自检
  memidx selftest --full                      # 完整测试（含API）
  memidx config                               # 配置向导
  memidx stats                                # 数据库统计

💡 详细帮助：memidx <command> --help
"""
    )
    parser.add_argument('--version', action='version', version='memoryindex 1.0.8')
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # ============================================================
    # 🆕 初始化功能
    # ============================================================
    init_parser = subparsers.add_parser('init', help='初始化数据库和环境（首次运行推荐）')
    init_parser.add_argument('--no-api', action='store_true', help='跳过 API 配置')
    # search_cli 中的 search_command 完整支持的参数
    search_parser = subparsers.add_parser('search', help='全文搜索')
    search_parser.add_argument('query', help='搜索查询（支持空格分隔多个关键词）')
    search_parser.add_argument('--tags', nargs='+', help='标签过滤')
    search_parser.add_argument('--field', choices=['all', 'report', 'transcript', 'ocr', 'topic'],
                              default='all', help='搜索字段')
    search_parser.add_argument('--sort', choices=['relevance', 'date', 'duration', 'title'],
                              default='relevance', help='排序方式')
    search_parser.add_argument('--limit', type=int, default=20, help='返回结果数')
    search_parser.add_argument('--offset', type=int, default=0, help='分页偏移')
    search_parser.add_argument('--min-relevance', type=float, default=0.0, help='最小相关性')
    search_parser.add_argument('--match-all', action='store_true', help='多关键词AND逻辑（默认OR）')
    search_parser.add_argument('--exact', action='store_true', help='精确搜索（默认模糊搜索）')
    search_parser.add_argument('--show-all-matches', action='store_true', help='显示所有匹配片段（默认每个视频只显示一次）')
    search_parser.add_argument('--json', action='store_true', help='JSON格式输出')
    search_parser.add_argument('-v', '--verbose', action='store_true', help='详细输出')
    
    # 标签搜索，与 tag_search_command 参数保持一致
    tags_parser = subparsers.add_parser('tags', help='按标签搜索')
    tags_parser.add_argument('--tags', nargs='+', required=True, help='标签列表')
    tags_parser.add_argument('--match-all', action='store_true', help='匹配所有标签（AND逻辑）')
    tags_parser.add_argument('--limit', type=int, default=20, help='返回结果数')
    tags_parser.add_argument('--offset', type=int, default=0, help='分页偏移')
    tags_parser.add_argument('--json', action='store_true', help='JSON格式输出')
    
    # 主题搜索
    topics_parser = subparsers.add_parser('topics', help='主题搜索')
    topics_parser.add_argument('query', help='主题关键词')
    topics_parser.add_argument('--limit', type=int, default=20, help='返回结果数')
    topics_parser.add_argument('--offset', type=int, default=0, help='分页偏移')
    topics_parser.add_argument('--json', action='store_true', help='JSON格式输出')
    
    # 列出热门标签
    list_tags_parser = subparsers.add_parser('list-tags', help='列出热门标签')
    list_tags_parser.add_argument('--limit', type=int, default=50, help='返回结果数')
    list_tags_parser.add_argument('--json', action='store_true', help='JSON格式输出')
    
    # 标签自动补全
    suggest_parser = subparsers.add_parser('suggest', help='标签自动补全')
    suggest_parser.add_argument('prefix', help='标签前缀')
    suggest_parser.add_argument('--limit', type=int, default=10, help='返回结果数')
    
    # 列出视频列表
    list_parser = subparsers.add_parser('list', help='列出所有视频')
    list_parser.add_argument('--limit', type=int, default=20, help='返回结果数')
    list_parser.add_argument('--offset', type=int, default=0, help='分页偏移')
    list_parser.add_argument('--json', action='store_true', help='JSON格式输出')
    
    # 展示视频详情
    show_parser = subparsers.add_parser('show', help='展示视频详情')
    show_parser.add_argument('id', type=int, help='视频ID')
    show_parser.add_argument('file', nargs='?', type=str, help='要直接展示的文件类型 (例如: report, transcript, ocr, info)')
    show_parser.add_argument('--json', action='store_true', help='JSON格式输出')
    show_parser.add_argument('--full', action='store_true', help='显示完整内容（包含转写、OCR等）')
    
    # 删除视频记录
    delete_parser = subparsers.add_parser('delete', help='删除视频记录')
    delete_parser.add_argument('id', type=int, help='视频ID')
    delete_parser.add_argument('--force', action='store_true', help='强制删除，不提示确认')
    
    # ============================================================
    # 📹 视频处理功能
    # ============================================================
    process_parser = subparsers.add_parser('process', help='处理视频文件')
    process_parser.add_argument('video', help='视频文件路径')
    process_parser.add_argument('--ocr', action='store_true', help='启用OCR识别')
    process_parser.add_argument('--ocr-engine', choices=['vision', 'paddle'], 
                               default='vision', help='OCR引擎')
    process_parser.add_argument('--use-gpu', action='store_true', help='使用GPU加速（PaddleOCR）')
    process_parser.add_argument('--skip-audio', action='store_true', help='跳过音频转写')
    process_parser.add_argument('--skip-llm', action='store_true', help='跳过LLM总结')
    
    # ============================================================
    # 📥 下载功能
    # ============================================================
    download_parser = subparsers.add_parser('download', help='下载在线视频')
    download_parser.add_argument('url', help='视频URL')
    download_parser.add_argument('--output', help='输出目录（默认: videos/）')
    download_parser.add_argument('--process', action='store_true', help='下载后自动处理')
    download_parser.add_argument('--ocr', action='store_true', help='处理时启用OCR')
    download_parser.add_argument('--force', action='store_true', help='强制重新下载')
    
    # ============================================================
    # 🌐 网页归档功能
    # ============================================================
    archive_parser = subparsers.add_parser('archive', help='归档网页为Markdown')
    archive_parser.add_argument('url', help='网页URL')
    archive_parser.add_argument('--output', help='输出文件路径')
    archive_parser.add_argument('--platform', 
                               choices=['zhihu', 'xiaohongshu', 'bilibili', 'reddit', 'twitter', 'auto'],
                               default='auto', help='平台类型（自动检测）')
    
    # ============================================================
    # 🔧 系统维护功能
    # ============================================================
    selftest_parser = subparsers.add_parser('selftest', help='系统自检')
    selftest_parser.add_argument('--full', action='store_true', help='完整测试（包含API）')
    
    config_parser = subparsers.add_parser('config', help='配置向导')
    config_parser.add_argument('--platform', 
                              choices=['xhs', 'xiaohongshu', 'zhihu', 'api'],
                              help='配置特定平台')
    
    stats_parser = subparsers.add_parser('stats', help='数据库统计信息')
    stats_parser.add_argument('--json', action='store_true', help='JSON格式输出')
    
    # 解析参数
    args = parser.parse_args()
    
    # 如果没有子命令，显示帮助
    if not args.command:
        parser.print_help()
        return 0
    
    # 路由到对应的处理函数
    try:
        if args.command in ['search', 'tags', 'topics', 'list-tags', 'suggest', 'list', 'show', 'delete']:
            # 搜索相关命令，全部委托给 cli.search_cli 中的实现
            from cli.search_cli import (
                search_command, tag_search_command, topic_search_command,
                list_tags_command, suggest_tags_command, list_command,
                show_command, delete_command,
            )
            command_map = {
                'search': search_command,
                'tags': tag_search_command,
                'topics': topic_search_command,
                'list-tags': list_tags_command,
                'suggest': suggest_tags_command,
                'list': list_command,
                'show': show_command,
                'delete': delete_command,
            }
            command_map[args.command](args)
            
        elif args.command == 'init':
            run_init(args)

        elif args.command == 'process':
            # 视频处理
            from core.process_video import process_video_cli
            process_video_cli(args)
            
        elif args.command == 'download':
            # 下载视频
            from core.video_downloader import download_cli
            download_cli(args)
            
        elif args.command == 'archive':
            # 网页归档
            from cli.archive_cli import archive_command
            archive_command(args)
            
        elif args.command == 'selftest':
            # 系统自检
            sys.argv = ['selftest']  # 重置 argv
            if args.full:
                sys.argv.append('--full')
            from scripts.selftest import main as selftest_main
            selftest_main()
            
        elif args.command == 'config':
            # 配置向导
            run_config_wizard(args)
            
        elif args.command == 'stats':
            # 数据库统计
            from cli.db_stats import show_stats
            show_stats(args)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  操作已取消")
        return 130
    except Exception as e:
        print(f"\n❌ 错误: {e}", file=sys.stderr)
        if '--debug' in sys.argv:
            import traceback
            traceback.print_exc()
        return 1
    
    return 0


def run_config_wizard(args):
    """配置向导"""
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("🔧 MemoryIndex 配置向导")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    if args.platform in ['xhs', 'xiaohongshu']:
        from scripts.configure_xhs_cookie import main as config_xhs
        config_xhs()
    elif args.platform == 'zhihu':
        from scripts.configure_zhihu_cookie import main as config_zhihu
        config_zhihu()
    elif args.platform == 'api':
        configure_api()
    else:
        # 显示配置菜单
        print("\n请选择要配置的项目：")
        print("  1. API密钥（GROQ_API_KEY）")
        print("  2. 小红书Cookie")
        print("  3. 知乎Cookie")
        print("  4. 查看当前配置")
        print("  0. 退出")
        
        try:
            choice = input("\n请输入选项 [0-4]: ").strip()
            if choice == '1':
                configure_api()
            elif choice == '2':
                from scripts.configure_xhs_cookie import main as config_xhs
                config_xhs()
            elif choice == '3':
                from scripts.configure_zhihu_cookie import main as config_zhihu
                config_zhihu()
            elif choice == '4':
                show_current_config()
            elif choice == '0':
                print("已退出")
            else:
                print("❌ 无效选项")
        except (EOFError, KeyboardInterrupt):
            print("\n\n⚠️  已取消")


def configure_api():
    """配置API密钥"""
    import os
    from pathlib import Path
    from dotenv import load_dotenv, set_key
    
    env_path = Path.home() / '.memoryindex' / '.env'
    env_path.parent.mkdir(parents=True, exist_ok=True)
    
    if not env_path.exists():
        env_path.touch()
    
    load_dotenv(env_path)
    
    print("\n━━ API 配置 ━━")
    print("当前配置文件:", env_path)
    
    current_key = os.getenv('GROQ_API_KEY', '')
    if current_key:
        masked = current_key[:8] + '*' * (len(current_key) - 12) + current_key[-4:] if len(current_key) > 12 else '***'
        print(f"当前密钥: {masked}")
    else:
        print("当前密钥: 未设置")
    
    print("\n请输入新的 GROQ_API_KEY（留空保持不变）:")
    new_key = input("API Key: ").strip()
    
    if new_key:
        set_key(env_path, 'GROQ_API_KEY', new_key)
        print("✅ API密钥已更新")
    else:
        print("⏭️  跳过更新")


def show_current_config():
    """显示当前配置"""
    import os
    from pathlib import Path
    from dotenv import load_dotenv
    
    env_path = Path.home() / '.memoryindex' / '.env'
    load_dotenv(env_path)
    
    print("\n━━ 当前配置 ━━")
    print(f"配置文件: {env_path}")
    print(f"存在: {'✅' if env_path.exists() else '❌'}")
    
    api_key = os.getenv('GROQ_API_KEY', '')
    if api_key:
        masked = api_key[:8] + '*' * 8 + api_key[-4:]
        print(f"GROQ_API_KEY: {masked}")
    else:
        print("GROQ_API_KEY: ❌ 未设置")
    
    # Cookie 配置
    cookie_dir = Path.home() / '.memoryindex' / 'cookies'
    if cookie_dir.exists():
        cookies = list(cookie_dir.glob('*.txt'))
        if cookies:
            print(f"\nCookies ({len(cookies)}个):")
            for cookie in cookies:
                print(f"  - {cookie.stem}")
        else:
            print("\nCookies: 未配置")
    else:
        print("\nCookies: 未配置")


if __name__ == '__main__':
    sys.exit(main())
