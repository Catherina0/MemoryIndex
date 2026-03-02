#!/usr/bin/env python3
"""
搜索命令行工具
提供便捷的搜索界面
"""
import sys
import warnings
import argparse
import json
from pathlib import Path
from typing import List
from tabulate import tabulate

# 过滤第三方库的已知警告
warnings.filterwarnings('ignore', message='pkg_resources is deprecated')
warnings.filterwarnings('ignore', category=SyntaxWarning, module='whoosh')

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from db import SearchRepository
from db.search import SearchField, SortBy


def print_formatted_table(table_data: list, headers: list):
    """打印去除网格横线的表格"""
    text = tabulate(table_data, headers=headers, tablefmt='grid')
    # 替换所有以 + 开头的网格线为空行
    lines = ['' if line.startswith('+') else line for line in text.split('\n')]
    print('\n'.join(lines))


def format_duration(seconds: float) -> str:
    """格式化时长"""
    if not seconds:
        return 'N/A'
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}:{secs:02d}"


def format_timestamp(seconds: float) -> str:
    """格式化时间戳"""
    if not seconds:
        return 'N/A'
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"


def truncate_text(text: str, max_length: int = 80) -> str:
    """截断文本"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + '...'


def search_command(args):
    """全文搜索命令"""
    repo = SearchRepository()
    
    # 解析搜索字段
    field = SearchField(args.field) if args.field else SearchField.ALL
    
    # 解析排序方式
    sort_by = SortBy(args.sort) if args.sort else SortBy.RELEVANCE
    
    # 执行搜索
    results = repo.search(
        query=args.query,
        tags=args.tags,
        fields=field,
        limit=args.limit,
        offset=args.offset,
        sort_by=sort_by,
        min_relevance=args.min_relevance,
        group_by_video=not args.show_all_matches,  # 默认聚合，除非指定显示所有
        match_all_keywords=getattr(args, 'match_all', False),  # 多关键词匹配逻辑
        fuzzy=not getattr(args, 'exact', False)  # 默认模糊搜索，除非指定精确
    )
    
    if not results:
        print("❌ 未找到匹配结果")
        return
    
    # 输出结果
    if args.json:
        # JSON 格式输出
        print(json.dumps(
            [r.to_dict() for r in results],
            ensure_ascii=False,
            indent=2
        ))
    else:
        # 表格格式输出
        print(f"\n🔍 找到 {len(results)} 个结果:\n")
        
        table_data = []
        for i, result in enumerate(results, 1):
            table_data.append([
                i,
                result.video_id,
                truncate_text(result.video_title, 30),
                result.source_field,
                truncate_text(result.matched_snippet, 50),
                format_timestamp(result.timestamp_seconds),
                f"{result.relevance_score:.2f}",
                ', '.join(result.tags[:3]) if result.tags else '-'
            ])
        
        headers = ['#', 'ID', '视频标题', '来源', '匹配片段', '时间点', '相关性', '标签']
        print_formatted_table(table_data, headers)
        
        # 详细信息
        if args.verbose:
            print("\n📝 详细信息:\n")
            for i, result in enumerate(results, 1):
                print(f"[{i}] {result.video_title}")
                print(f"  ID: {result.video_id}")
                print(f"  来源: {result.source_field}")
                print(f"  标签: {', '.join(result.tags)}")
                print(f"  时间: {format_timestamp(result.timestamp_seconds)}")
                print(f"  相关性: {result.relevance_score:.3f}")
                print(f"  片段: {result.matched_snippet}")
                print(f"  文件: {result.file_path}")
                print()


def tag_search_command(args):
    """标签搜索命令"""
    repo = SearchRepository()
    
    results = repo.search_by_tags(
        tags=args.tags,
        match_all=args.match_all,
        limit=args.limit,
        offset=args.offset
    )
    
    if not results:
        print("❌ 未找到匹配结果")
        return
    
    print(f"\n🏷️  找到 {len(results)} 个视频:\n")
    
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2, default=str))
    else:
        table_data = []
        for i, video in enumerate(results, 1):
            table_data.append([
                i,
                video['id'],
                truncate_text(video['title'], 40),
                video['source_type'],
                format_duration(video.get('duration_seconds')),
                video.get('tags', '-')
            ])
        
        headers = ['#', 'ID', '标题', '来源', '时长', '标签']
        print_formatted_table(table_data, headers)


def tags_command(args):
    """兼容主 CLI 的别名，等价于 tag_search_command"""
    return tag_search_command(args)


def topic_search_command(args):
    """主题搜索命令"""
    repo = SearchRepository()
    
    results = repo.search_topics(
        query=args.query,
        limit=args.limit,
        offset=args.offset
    )
    
    if not results:
        print("❌ 未找到匹配结果")
        return
    
    print(f"\n📚 找到 {len(results)} 个主题:\n")
    
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2, default=str))
    else:
        for i, topic in enumerate(results, 1):
            print(f"[{i}] {topic['title']}")
            print(f"  视频: {topic['video_title']}")
            print(f"  时间: {format_timestamp(topic.get('start_time'))} - {format_timestamp(topic.get('end_time'))}")
            if topic.get('summary'):
                print(f"  摘要: {truncate_text(topic['summary'], 100)}")
            if topic.get('video_tags'):
                print(f"  标签: {topic['video_tags']}")
            print()


def topics_command(args):
    """兼容主 CLI 的别名，等价于 topic_search_command"""
    return topic_search_command(args)


def list_tags_command(args):
    """列出热门标签"""
    repo = SearchRepository()
    
    tags = repo.get_popular_tags(limit=args.limit)
    
    if not tags:
        print("❌ 暂无标签")
        return
    
    print(f"\n🏷️  热门标签 (Top {len(tags)}):\n")
    
    if args.json:
        print(json.dumps(tags, ensure_ascii=False, indent=2, default=str))
    else:
        table_data = []
        for i, tag in enumerate(tags, 1):
            table_data.append([
                i,
                tag['name'],
                tag.get('category', '-'),
                tag['video_count'],
                tag['count']
            ])
        
        headers = ['#', '标签名', '分类', '视频数', '使用次数']
        print_formatted_table(table_data, headers)


def suggest_tags_command(args):
    """标签自动补全"""
    repo = SearchRepository()
    
    suggestions = repo.suggest_tags(args.prefix, limit=args.limit)
    
    if not suggestions:
        print(f"❌ 无匹配的标签: {args.prefix}")
        return
    
    print(f"\n💡 标签建议 (前缀: '{args.prefix}'):\n")
    for tag in suggestions:
        print(f"  • {tag}")


def suggest_command(args):
    """兼容主 CLI 的别名，等价于 suggest_tags_command"""
    return suggest_tags_command(args)


def show_command(args):
    """展示特定ID的视频详情"""
    from db import VideoRepository
    repo = VideoRepository()
    
    video = repo.get_video_by_id(args.id)
    
    if not video:
        print(f"\n❌ 未找到 ID 为 {args.id} 的视频")
        return
    
    # 获取标签
    tags = repo.get_video_tags(args.id)
    
    # 获取主题
    topics = repo.get_topics(args.id)
    
    # 获取文件（报告、转写、OCR）
    artifacts = repo.get_artifacts(args.id)
    
    # 如果指定了具体文件类型，直接输出其内容，不显示其它额外信息
    if getattr(args, 'file', None):
        target_type = args.file.lower()
        # 寻找匹配类型的产物
        target_artifact = next((a for a in artifacts if a.artifact_type and a.artifact_type.value.lower() == target_type), None)
        
        if not target_artifact:
            print(f"❌ 未找到类型为 '{target_type}' 的相关文件。")
            available = [a.artifact_type.value for a in artifacts if a.artifact_type]
            if available:
                print(f"💡 当前可用的文件类型有: {', '.join(available)}")
            return
            
        print(f"=== {target_type.upper()} 内容 ({target_artifact.file_path or '内嵌'}) ===")
        if target_artifact.content_text:
            print(target_artifact.content_text)
        elif target_artifact.file_path:
            # 尝试从文件读取
            import os
            try:
                with open(target_artifact.file_path, 'r', encoding='utf-8') as f:
                    print(f.read())
            except Exception as e:
                print(f"❌ 无法读取文件 {target_artifact.file_path}: {e}")
        else:
            print("该文件无内容。")
        return
    
    # JSON 输出
    if args.json:
        result = {
            'id': video.id,
            'title': video.title,
            'source_type': video.source_type.value if video.source_type else None,
            'source_url': video.source_url,
            'file_path': video.file_path,
            'duration_seconds': video.duration_seconds,
            'status': video.status.value if video.status else None,
            'created_at': str(video.created_at) if video.created_at else None,
            'processed_at': str(video.processed_at) if video.processed_at else None,
            'tags': tags,
            'topics': [
                {
                    'title': t.title,
                    'start_time': t.start_time,
                    'end_time': t.end_time,
                    'summary': t.summary
                } for t in topics
            ],
            'artifacts': [
                {
                    'type': a.artifact_type.value if a.artifact_type else None,
                    'file_path': a.file_path,
                    'content_preview': a.content_text[:500] + '...' if a.content_text and len(a.content_text) > 500 else a.content_text
                } for a in artifacts
            ] if not args.full else [
                {
                    'type': a.artifact_type.value if a.artifact_type else None,
                    'file_path': a.file_path,
                    'content': a.content_text
                } for a in artifacts
            ]
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    
    # 格式化输出
    print(f"\n{'='*60}")
    print(f"📹 视频详情 (ID: {video.id})")
    print(f"{'='*60}")
    
    print(f"\n📌 基本信息")
    print(f"  标题: {video.title}")
    print(f"  来源: {video.source_type.value if video.source_type else 'N/A'}")
    if video.source_url:
        print(f"  URL: {video.source_url}")
    print(f"  文件: {video.file_path}")
    print(f"  时长: {format_duration(video.duration_seconds)}")
    print(f"  状态: {video.status.value if video.status else 'N/A'}")
    print(f"  创建: {video.created_at}")
    if video.processed_at:
        print(f"  处理: {video.processed_at}")
    
    if tags:
        print(f"\n🏷️  标签")
        print(f"  {', '.join(tags)}")
    
    # 从 artifacts 中获取报告内容，提取摘要和主要内容概括
    report_artifact = next((a for a in artifacts if a.artifact_type and a.artifact_type.value == 'report'), None)
    if report_artifact and report_artifact.content_text:
        content = report_artifact.content_text
        lines = content.split('\n')
        
        # 提取摘要部分
        summary_lines = []
        in_summary = False
        for line in lines:
            # 检测摘要标题
            if '摘要' in line and ('#' in line or line.strip().startswith('摘要')):
                in_summary = True
                continue
            # 检测下一个章节标题（结束摘要）
            if in_summary and line.strip().startswith('#'):
                break
            if in_summary and line.strip():
                summary_lines.append(line)
        
        if summary_lines:
            print(f"\n📝 摘要")
            for line in summary_lines:
                print(f"  {line}")
        
        # 提取详细的主要内容概括
        detail_lines = []
        in_detail = False
        for line in lines:
            # 检测主要内容概括标题
            if ('详细' in line and '主要内容' in line) or ('主要内容概括' in line):
                in_detail = True
                continue
            # 检测下一个章节标题（结束）
            if in_detail and line.strip().startswith('#') and '详细' not in line:
                break
            if in_detail and line.strip():
                detail_lines.append(line)
        
        if detail_lines:
            print(f"\n📋 主要内容概括")
            for line in detail_lines[:30]:  # 最多显示30行
                print(f"  {line}")
            if len(detail_lines) > 30:
                print(f"  ... (共 {len(detail_lines)} 行)")
    
    if artifacts:
        # 只显示每种类型的最新文件
        seen_types = set()
        latest_artifacts = []
        for a in artifacts:
            type_name = a.artifact_type.value if a.artifact_type else 'unknown'
            if type_name not in seen_types:
                seen_types.add(type_name)
                latest_artifacts.append(a)
        
        print(f"\n📄 相关文件 ({len(latest_artifacts)} 个)")
        for a in latest_artifacts:
            type_name = a.artifact_type.value if a.artifact_type else 'unknown'
            print(f"  • {type_name}: {a.file_path or '(内嵌)'}")
            if args.full and a.content_text:
                print(f"\n--- {type_name} 内容 ---")
                print(a.content_text[:2000] if len(a.content_text) > 2000 else a.content_text)
                if len(a.content_text) > 2000:
                    print(f"\n... (共 {len(a.content_text)} 字符，已截断)")
                print(f"--- {type_name} 结束 ---\n")
    
    print(f"\n{'='*60}")


def delete_command(args):
    """删除特定ID的视频记录"""
    from db import VideoRepository
    from db.whoosh_search import WhooshSearchIndex
    
    video_repo = VideoRepository()
    whoosh_index = WhooshSearchIndex()
    
    # 检查视频是否存在
    video = video_repo.get_video_by_id(args.id)
    if not video:
        print(f"\n❌ 未找到 ID 为 {args.id} 的视频")
        return
    
    # 显示视频信息
    print(f"\n📹 即将删除以下视频记录：")
    print(f"   ID: {video.id}")
    print(f"   标题: {video.title}")
    print(f"   来源: {video.source_type.value if video.source_type else 'N/A'}")
    print(f"   URL: {video.source_url}")
    print(f"   文件: {video.file_path}")
    
    # 确认删除（除非使用 --force）
    if not args.force:
        confirm = input("\n⚠️  确认删除？此操作不可恢复！(yes/no): ")
        if confirm.lower() not in ['yes', 'y']:
            print("❌ 已取消删除")
            return
    
    # 执行删除
    try:
        # 1. 从数据库删除
        success = video_repo.delete_video(args.id)
        if not success:
            print(f"❌ 删除失败：视频记录不存在")
            return
        
        # 2. 从Whoosh搜索索引删除
        whoosh_index.delete_video(args.id)
        
        print(f"\n✅ 成功删除视频记录 ID={args.id}")
        print(f"   ℹ️  注意：文件未被删除，如需删除请手动操作：")
        print(f"   rm -rf \"{video.file_path}\"")
        
    except Exception as e:
        print(f"\n❌ 删除失败: {e}")


def list_command(args):
    """列出所有视频"""
    from db import VideoRepository
    repo = VideoRepository()
    
    videos = repo.list_videos_with_summary(limit=args.limit, offset=args.offset)
    
    if not videos:
        print("\n❌ 数据库中没有视频")
        return
    
    # JSON 输出
    if args.json:
        # 转换 datetime 为字符串
        for v in videos:
            if 'created_at' in v and v['created_at']:
                v['created_at'] = str(v['created_at'])
        print(json.dumps(videos, ensure_ascii=False, indent=2))
        return
    
    # 表格输出
    print(f"\n📹 视频列表 (共 {len(videos)} 条):\n")
    
    table_data = []
    for i, video in enumerate(videos, 1):
        table_data.append([
            i,
            video['id'],
            truncate_text(video['title'], 30),
            video['source_type'],
            format_duration(video['duration']),
            truncate_text(', '.join(video['tags']), 30) if video['tags'] else '无',
            truncate_text(video['summary'], 50)
        ])
    
    headers = ['#', 'ID', '标题', '来源', '时长', '标签', '摘要']
    print_formatted_table(table_data, headers)


def main():
    parser = argparse.ArgumentParser(
        prog='memidx',
        description='MemoryIndex - 智能视频知识库搜索系统',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 MemoryIndex - 快速使用指南
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🚀 基础搜索：
  memidx search "关键词"                       # 全文搜索（转写+OCR+摘要）
  memidx search "人工智能" --field transcript  # 仅搜索语音转写
  memidx search "机器学习" --field ocr         # 仅搜索 OCR 文字
  memidx search "深度学习" --match-all         # AND 逻辑（必须包含所有词）
  memidx search "神经网络" --exact             # 精确匹配

🏷️  标签管理：
  memidx tags --tags 教育 科技                # 按标签查找（OR）
  memidx tags --tags 教育 科技 --match-all    # 按标签查找（AND）
  memidx list-tags                            # 列出所有标签
  memidx list-tags --limit 20                 # 列出热门标签（Top 20）
  memidx suggest "机器"                        # 标签自动补全

📂 视频管理：
  memidx list                                 # 列出所有视频
  memidx list --limit 10                      # 列出最新 10 个视频
  memidx show 123                             # 查看视频详情（ID=123）
  memidx topics "AI"                          # 搜索包含特定主题的视频
  memidx delete 123                           # 删除视频记录

💡 高级选项：
  memidx search "关键词" --sort date          # 按日期排序
  memidx search "关键词" --limit 50           # 返回 50 条结果
  memidx search "关键词" --json               # JSON 格式输出
  memidx search "关键词" --min-relevance 0.5  # 最小相关度 0.5

🎬 视频处理（另见 memidx-process --help）：
  memidx-process video.mp4                    # 处理本地视频
  memidx-process video.mp4 --with-frames      # 包含 OCR 识别
  memidx-download "https://youtu.be/xxx"      # 下载并处理在线视频

🌐 网页归档（另见 memidx-archive --help）：
  memidx-archive "https://zhihu.com/xxx"      # 归档网页为 Markdown

💡 更多帮助：memidx <command> --help
"""
    )
    parser.add_argument('--version', action='version', version='memoryindex 1.0.4')
    
    subparsers = parser.add_subparsers(dest='command', help='子命令')
    
    # 全文搜索
    search_parser = subparsers.add_parser('search', help='全文搜索（支持多关键词）')
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
    search_parser.set_defaults(func=search_command)
    
    # 标签搜索
    tags_parser = subparsers.add_parser('tags', help='按标签搜索')
    tags_parser.add_argument('--tags', nargs='+', required=True, help='标签列表')
    tags_parser.add_argument('--match-all', action='store_true', help='匹配所有标签（AND逻辑）')
    tags_parser.add_argument('--limit', type=int, default=20, help='返回结果数')
    tags_parser.add_argument('--offset', type=int, default=0, help='分页偏移')
    tags_parser.add_argument('--json', action='store_true', help='JSON格式输出')
    tags_parser.set_defaults(func=tag_search_command)
    
    # 主题搜索
    topics_parser = subparsers.add_parser('topics', help='搜索主题')
    topics_parser.add_argument('query', help='搜索查询')
    topics_parser.add_argument('--limit', type=int, default=20, help='返回结果数')
    topics_parser.add_argument('--offset', type=int, default=0, help='分页偏移')
    topics_parser.add_argument('--json', action='store_true', help='JSON格式输出')
    topics_parser.set_defaults(func=topic_search_command)
    
    # 列出标签
    list_tags_parser = subparsers.add_parser('list-tags', help='列出热门标签')
    list_tags_parser.add_argument('--limit', type=int, default=50, help='返回结果数')
    list_tags_parser.add_argument('--json', action='store_true', help='JSON格式输出')
    list_tags_parser.set_defaults(func=list_tags_command)
    
    # 标签建议
    suggest_parser = subparsers.add_parser('suggest', help='标签自动补全')
    suggest_parser.add_argument('prefix', help='标签前缀')
    suggest_parser.add_argument('--limit', type=int, default=10, help='返回结果数')
    suggest_parser.set_defaults(func=suggest_tags_command)
    
    # 列出视频
    list_parser = subparsers.add_parser('list', help='列出所有视频')
    list_parser.add_argument('--limit', type=int, default=20, help='返回结果数')
    list_parser.add_argument('--offset', type=int, default=0, help='分页偏移')
    list_parser.add_argument('--json', action='store_true', help='JSON格式输出')
    list_parser.set_defaults(func=list_command)
    
    # 展示视频详情
    show_parser = subparsers.add_parser('show', help='展示特定ID的视频详情')
    show_parser.add_argument('id', type=int, help='视频ID')
    show_parser.add_argument('file', nargs='?', type=str, help='要直接展示的文件类型 (例如: report, transcript, ocr, info)')
    show_parser.add_argument('--json', action='store_true', help='JSON格式输出')
    show_parser.add_argument('--full', action='store_true', help='显示完整内容（包含转写、OCR等）')
    show_parser.set_defaults(func=show_command)
    
    # 删除视频记录
    delete_parser = subparsers.add_parser('delete', help='删除特定ID的视频记录')
    delete_parser.add_argument('id', type=int, help='视频ID')
    delete_parser.add_argument('--force', action='store_true', help='强制删除，不提示确认')
    delete_parser.set_defaults(func=delete_command)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # 执行命令
    args.func(args)


if __name__ == '__main__':
    main()
