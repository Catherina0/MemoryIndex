#!/usr/bin/env python3
"""
数据库详细统计工具
提供更深入的数据分析
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any
from tabulate import tabulate

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from db import VideoRepository
from db.schema import get_connection
from db.tag_filters import get_hidden_tag_sql


def get_archive_stats() -> Dict[str, Any]:
    """获取网页归档的详细统计"""
    conn = get_connection()
    try:
        stats = {}
        
        # 网页归档按平台统计
        cursor = conn.execute("""
            SELECT source_type, COUNT(*) as count,
                   AVG(file_size_bytes) as avg_size
            FROM videos 
            WHERE source_type IN ('zhihu', 'reddit', 'twitter', 'web_archive')
            GROUP BY source_type
        """)
        stats['by_platform'] = [dict(row) for row in cursor.fetchall()]
        
        # 最近归档的网页
        cursor = conn.execute("""
            SELECT id, title, source_type, source_url, created_at
            FROM videos 
            WHERE source_type IN ('zhihu', 'reddit', 'twitter', 'web_archive')
            ORDER BY created_at DESC
            LIMIT 10
        """)
        stats['recent'] = [dict(row) for row in cursor.fetchall()]
        
        # 归档网页的OCR使用率
        cursor = conn.execute("""
            SELECT 
                COUNT(DISTINCT v.id) as total,
                COUNT(DISTINCT a.video_id) as with_ocr
            FROM videos v
            LEFT JOIN artifacts a ON v.id = a.video_id AND a.artifact_type = 'ocr'
            WHERE v.source_type IN ('zhihu', 'reddit', 'twitter', 'web_archive')
        """)
        row = cursor.fetchone()
        stats['ocr_usage'] = {
            'total': row['total'],
            'with_ocr': row['with_ocr'],
            'percentage': (row['with_ocr'] / row['total'] * 100) if row['total'] > 0 else 0
        }
        
        return stats
    finally:
        conn.close()


def get_video_stats() -> Dict[str, Any]:
    """获取视频文件的详细统计"""
    conn = get_connection()
    try:
        stats = {}
        
        # 视频按平台统计（包含时长）
        cursor = conn.execute("""
            SELECT source_type, COUNT(*) as count,
                   AVG(duration_seconds) as avg_duration,
                   SUM(duration_seconds) as total_duration,
                   AVG(file_size_bytes) as avg_size
            FROM videos 
            WHERE source_type IN ('local', 'bilibili', 'youtube', 'xiaohongshu')
                  AND duration_seconds IS NOT NULL
            GROUP BY source_type
        """)
        stats['by_platform'] = [dict(row) for row in cursor.fetchall()]
        
        # 总时长
        cursor = conn.execute("""
            SELECT SUM(duration_seconds) as total
            FROM videos 
            WHERE duration_seconds IS NOT NULL
        """)
        stats['total_duration'] = cursor.fetchone()['total'] or 0
        
        # OCR使用率
        cursor = conn.execute("""
            SELECT 
                COUNT(DISTINCT v.id) as total,
                COUNT(DISTINCT a.video_id) as with_ocr
            FROM videos v
            LEFT JOIN artifacts a ON v.id = a.video_id AND a.artifact_type = 'ocr'
            WHERE v.source_type IN ('local', 'bilibili', 'youtube', 'xiaohongshu')
        """)
        row = cursor.fetchone()
        stats['ocr_usage'] = {
            'total': row['total'],
            'with_ocr': row['with_ocr'],
            'percentage': (row['with_ocr'] / row['total'] * 100) if row['total'] > 0 else 0
        }
        
        return stats
    finally:
        conn.close()


def get_tag_stats(db_path: str = None) -> Dict[str, Any]:
    """获取标签使用统计"""
    conn = get_connection(db_path)
    try:
        stats = {}
        visible_clause, visible_params = get_hidden_tag_sql("t.name")
        
        # 最常用的标签
        cursor = conn.execute(f"""
            SELECT t.name, COUNT(*) as usage_count
            FROM video_tags vt
            JOIN tags t ON vt.tag_id = t.id
            WHERE {visible_clause}
            GROUP BY t.name
            ORDER BY usage_count DESC, t.name ASC
            LIMIT 20
        """, visible_params)
        stats['top_tags'] = [dict(row) for row in cursor.fetchall()]
        
        # 标签使用分布
        cursor = conn.execute(f"""
            SELECT usage_count, COUNT(*) as tag_count
            FROM (
                SELECT COUNT(*) as usage_count
                FROM video_tags vt
                JOIN tags t ON vt.tag_id = t.id
                WHERE {visible_clause}
                GROUP BY vt.tag_id
            )
            GROUP BY usage_count
            ORDER BY usage_count DESC
        """, visible_params)
        stats['distribution'] = [dict(row) for row in cursor.fetchall()]
        
        return stats
    finally:
        conn.close()


def format_duration(seconds: float) -> str:
    """格式化时长"""
    if not seconds:
        return 'N/A'
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def format_size(bytes: float) -> str:
    """格式化文件大小"""
    if not bytes:
        return 'N/A'
    mb = bytes / 1024 / 1024
    if mb > 1024:
        return f"{mb / 1024:.2f} GB"
    return f"{mb:.2f} MB"


def show_stats(args):
    """统一CLI适配函数"""
    # 如果没有指定参数，默认显示所有
    show_all = not (hasattr(args, 'archives') or hasattr(args, 'videos') or hasattr(args, 'tags'))
    
    if show_all or getattr(args, 'archives', False):
        print("\n" + "=" * 60)
        print("🌐 网页归档详细统计")
        print("=" * 60)
        
        archive_stats = get_archive_stats()
        
        # 按平台统计
        if archive_stats['by_platform']:
            print("\n📊 按平台统计:")
            table = []
            for item in archive_stats['by_platform']:
                platform_names = {
                    'twitter': 'Twitter/X',
                    'zhihu': '知乎',
                    'reddit': 'Reddit',
                    'web_archive': '通用网页'
                }
                platform = platform_names.get(item['source_type'], item['source_type'])
                table.append([
                    platform,
                    item['count'],
                    format_size(item['avg_size'])
                ])
            from tabulate import tabulate
            print(tabulate(table, headers=['平台', '数量', '平均大小'], tablefmt='simple'))
    
    if show_all or getattr(args, 'videos', False):
        # TODO: 添加视频统计
        pass
    
    if show_all or getattr(args, 'tags', False):
        # TODO: 添加标签统计
        pass


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='数据库详细统计')
    parser.add_argument('--archives', action='store_true', help='显示网页归档统计')
    parser.add_argument('--videos', action='store_true', help='显示视频文件统计')
    parser.add_argument('--tags', action='store_true', help='显示标签统计')
    parser.add_argument('--all', action='store_true', help='显示所有统计')
    
    args = parser.parse_args()
    
    # 如果没有指定参数，默认显示所有
    if not (args.archives or args.videos or args.tags):
        args.all = True
    
    if args.all or args.archives:
        print("\n" + "=" * 60)
        print("🌐 网页归档详细统计")
        print("=" * 60)
        
        archive_stats = get_archive_stats()
        
        # 按平台统计
        if archive_stats['by_platform']:
            print("\n📊 按平台统计:")
            table = []
            for item in archive_stats['by_platform']:
                platform_names = {
                    'twitter': 'Twitter/X',
                    'zhihu': '知乎',
                    'reddit': 'Reddit',
                    'web_archive': '通用网页'
                }
                platform = platform_names.get(item['source_type'], item['source_type'])
                table.append([
                    platform,
                    item['count'],
                    format_size(item['avg_size'])
                ])
            print(tabulate(table, headers=['平台', '数量', '平均大小'], tablefmt='simple'))
        
        # OCR使用率
        ocr_usage = archive_stats['ocr_usage']
        print(f"\n🔍 OCR使用情况:")
        print(f"  总计: {ocr_usage['total']} 条")
        print(f"  使用OCR: {ocr_usage['with_ocr']} 条 ({ocr_usage['percentage']:.1f}%)")
        
        # 最近归档
        if archive_stats['recent']:
            print(f"\n📅 最近归档 (前10条):")
            table = []
            for item in archive_stats['recent'][:5]:  # 只显示前5条
                title = item['title'][:40] + '...' if len(item['title']) > 40 else item['title']
                # 处理日期格式
                if isinstance(item['created_at'], str):
                    created = datetime.fromisoformat(item['created_at']).strftime('%m-%d %H:%M')
                else:
                    created = item['created_at'].strftime('%m-%d %H:%M') if item['created_at'] else 'N/A'
                table.append([
                    item['id'],
                    title,
                    item['source_type'],
                    created
                ])
            print(tabulate(table, headers=['ID', '标题', '平台', '归档时间'], tablefmt='simple'))
    
    if args.all or args.videos:
        print("\n" + "=" * 60)
        print("🎥 视频文件详细统计")
        print("=" * 60)
        
        video_stats = get_video_stats()
        
        # 按平台统计
        if video_stats['by_platform']:
            print("\n📊 按平台统计:")
            table = []
            for item in video_stats['by_platform']:
                platform_names = {
                    'local': '本地视频',
                    'bilibili': 'B站',
                    'youtube': 'YouTube',
                    'xiaohongshu': '小红书'
                }
                platform = platform_names.get(item['source_type'], item['source_type'])
                table.append([
                    platform,
                    item['count'],
                    format_duration(item['avg_duration']),
                    format_duration(item['total_duration']),
                    format_size(item['avg_size'])
                ])
            print(tabulate(table, headers=['平台', '数量', '平均时长', '总时长', '平均大小'], tablefmt='simple'))
        
        # 总时长
        print(f"\n⏱️  视频总时长: {format_duration(video_stats['total_duration'])}")
        
        # OCR使用率
        ocr_usage = video_stats['ocr_usage']
        print(f"\n🔍 OCR使用情况:")
        print(f"  总计: {ocr_usage['total']} 条")
        print(f"  使用OCR: {ocr_usage['with_ocr']} 条 ({ocr_usage['percentage']:.1f}%)")
    
    if args.all or args.tags:
        print("\n" + "=" * 60)
        print("🏷️  标签使用统计")
        print("=" * 60)
        
        tag_stats = get_tag_stats()
        
        # 最常用标签
        if tag_stats['top_tags']:
            print("\n📊 最常用标签 (Top 20):")
            table = []
            for i, item in enumerate(tag_stats['top_tags'], 1):
                table.append([i, item['name'], item['usage_count']])
            print(tabulate(table, headers=['#', '标签', '使用次数'], tablefmt='simple'))
    
    print("\n" + "=" * 60 + "\n")


if __name__ == '__main__':
    main()
