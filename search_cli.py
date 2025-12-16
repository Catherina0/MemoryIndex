#!/usr/bin/env python3
"""
搜索命令行工具
提供便捷的搜索界面
"""
import argparse
import json
from typing import List
from tabulate import tabulate

from db import SearchRepository
from db.search import SearchField, SortBy


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
        min_relevance=args.min_relevance
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
                truncate_text(result.video_title, 30),
                result.source_field,
                truncate_text(result.matched_snippet, 50),
                format_timestamp(result.timestamp_seconds),
                f"{result.relevance_score:.2f}",
                ', '.join(result.tags[:3]) if result.tags else '-'
            ])
        
        headers = ['#', '视频标题', '来源', '匹配片段', '时间点', '相关性', '标签']
        print(tabulate(table_data, headers=headers, tablefmt='grid'))
        
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
        print(tabulate(table_data, headers=headers, tablefmt='grid'))


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
        print(tabulate(table_data, headers=headers, tablefmt='grid'))


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


def main():
    parser = argparse.ArgumentParser(
        description='知识库搜索工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 全文搜索
  python search_cli.py search "机器学习"
  
  # 在转写中搜索
  python search_cli.py search "人工智能" --field transcript
  
  # 按标签搜索
  python search_cli.py tags --tags 教育 科技 --match-all
  
  # 搜索主题
  python search_cli.py topics "神经网络"
  
  # 列出热门标签
  python search_cli.py list-tags --limit 20
  
  # 标签自动补全
  python search_cli.py suggest "机器"
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='子命令')
    
    # 全文搜索
    search_parser = subparsers.add_parser('search', help='全文搜索')
    search_parser.add_argument('query', help='搜索查询')
    search_parser.add_argument('--tags', nargs='+', help='标签过滤')
    search_parser.add_argument('--field', choices=['all', 'report', 'transcript', 'ocr', 'topic'],
                              default='all', help='搜索字段')
    search_parser.add_argument('--sort', choices=['relevance', 'date', 'duration', 'title'],
                              default='relevance', help='排序方式')
    search_parser.add_argument('--limit', type=int, default=20, help='返回结果数')
    search_parser.add_argument('--offset', type=int, default=0, help='分页偏移')
    search_parser.add_argument('--min-relevance', type=float, default=0.0, help='最小相关性')
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
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # 执行命令
    args.func(args)


if __name__ == '__main__':
    main()
