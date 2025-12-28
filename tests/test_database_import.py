#!/usr/bin/env python3
"""
数据库导入测试脚本
使用 output 目录中的真实数据测试数据库功能
"""
import sys
import json
from pathlib import Path
from datetime import datetime
import re

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from db import VideoRepository
from db.models import Video, Artifact, Topic, TimelineEntry, SourceType, ArtifactType, ProcessingStatus


def extract_tags_from_text(text: str) -> list:
    """从文本中提取标签"""
    tags = []
    
    tag_patterns = [
        r'标签[：:]\s*(.+)',
        r'Tags[：:]\s*(.+)',
        r'关键词[：:]\s*(.+)',
        r'Keywords[：:]\s*(.+)',
    ]
    
    for pattern in tag_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            clean_match = re.sub(r'\*\*|\*|`|#|["""\'\'"]', '', match)
            tag_list = re.split(r'[,，、\s;；]+', clean_match.strip())
            tags.extend([t.strip() for t in tag_list if t.strip()])
    
    seen = set()
    unique_tags = []
    for tag in tags:
        tag = re.sub(r'[^\w\u4e00-\u9fa5\-]', '', tag)
        tag_lower = tag.lower()
        if tag_lower not in seen and len(tag) > 1 and len(tag) < 20:
            seen.add(tag_lower)
            unique_tags.append(tag)
    
    return unique_tags[:10]


def extract_topics_from_text(text: str) -> list:
    """从文本中提取主题"""
    topics = []
    lines = text.split('\n')
    
    for i, line in enumerate(lines):
        line = line.strip()
        if line.startswith('##') and not line.startswith('###'):
            title = line.lstrip('#').strip()
            
            skip_titles = ['AI 智能总结', '数据统计', '原始数据', '总结', '标签', 'Tags', '关键词']
            if any(skip in title for skip in skip_titles):
                continue
            
            time_match = re.search(r'\[?(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})\]?', line)
            
            if time_match:
                start_min, start_sec, end_min, end_sec = map(int, time_match.groups())
                start_time = start_min * 60 + start_sec
                end_time = end_min * 60 + end_sec
            else:
                start_time = 0
                end_time = 0
            
            description_lines = []
            for j in range(i + 1, min(i + 5, len(lines))):
                desc_line = lines[j].strip()
                if desc_line and not desc_line.startswith('#'):
                    description_lines.append(desc_line)
                elif desc_line.startswith('##'):
                    break
            
            description = ' '.join(description_lines)[:200]
            
            topics.append({
                'title': title[:100],
                'start_time': start_time,
                'end_time': end_time,
                'summary': description,
            })
    
    return topics[:20]


def import_directory(session_dir: Path, video_title: str = None, source_url: str = None):
    """
    导入一个 output 目录到数据库
    
    Args:
        session_dir: output 子目录路径
        video_title: 视频标题（可选，从目录名提取）
        source_url: 源URL（可选）
    """
    print(f"\n{'='*60}")
    print(f"📂 导入目录: {session_dir.name}")
    print(f"{'='*60}")
    
    # 从目录名提取视频标题
    if not video_title:
        # 去掉时间戳部分
        dir_name = session_dir.name
        parts = dir_name.rsplit('_', 2)
        if len(parts) >= 3 and parts[-2].isdigit() and parts[-1].isdigit():
            video_title = '_'.join(parts[:-2])
        else:
            video_title = dir_name
    
    # 判断来源
    if 'bilibili' in session_dir.name.lower() or 'BV' in session_dir.name:
        source_type = SourceType.BILIBILI
    elif 'youtube' in session_dir.name.lower():
        source_type = SourceType.YOUTUBE
    else:
        source_type = SourceType.LOCAL
    
    # 读取文件
    transcript_file = session_dir / "transcript_raw.md"
    ocr_file = session_dir / "ocr_raw.md"
    report_file = session_dir / "report.md"
    timeline_file = session_dir / "timeline.md"
    
    transcript_text = ""
    ocr_text = ""
    report_text = ""
    timeline_text = ""
    
    if transcript_file.exists():
        transcript_text = transcript_file.read_text(encoding='utf-8')
        print(f"   ✅ 读取语音转写 ({len(transcript_text)} 字符)")
    
    if ocr_file.exists():
        ocr_text = ocr_file.read_text(encoding='utf-8')
        print(f"   ✅ 读取OCR识别 ({len(ocr_text)} 字符)")
    
    if report_file.exists():
        report_text = report_file.read_text(encoding='utf-8')
        print(f"   ✅ 读取AI报告 ({len(report_text)} 字符)")
    
    if timeline_file.exists():
        timeline_text = timeline_file.read_text(encoding='utf-8')
        print(f"   ✅ 读取时间线 ({len(timeline_text)} 字符)")
    
    if not transcript_text and not ocr_text and not report_text:
        print("   ⚠️  没有找到可导入的数据文件")
        return None
    
    # 创建视频记录
    repo = VideoRepository()
    
    # 使用目录路径作为唯一标识
    import hashlib
    content_hash = hashlib.sha256(str(session_dir).encode()).hexdigest()
    
    # 检查是否已存在
    existing = repo.get_video_by_hash(content_hash)
    if existing:
        print(f"   ⚠️  视频已存在 (ID: {existing.id})，跳过...")
        return existing.id
    
    video = Video(
        content_hash=content_hash,
        video_id=None,
        source_type=source_type,
        source_url=source_url,
        platform_title=video_title,
        title=video_title,
        duration_seconds=None,
        file_path=str(session_dir),
        file_size_bytes=0,
        processing_config={'imported_from': str(session_dir)},
        status=ProcessingStatus.COMPLETED
    )
    
    video_id = repo.create_video(video)
    print(f"   ✅ 创建视频记录 (ID: {video_id})")
    
    # 保存产物
    if transcript_text:
        artifact = Artifact(
            video_id=video_id,
            artifact_type=ArtifactType.TRANSCRIPT,
            content_text=transcript_text,
            file_path=str(transcript_file),
            model_name="imported",
            char_count=len(transcript_text)
        )
        repo.save_artifact(artifact)
        print(f"   ✅ 保存语音转写产物")
    
    if ocr_text:
        artifact = Artifact(
            video_id=video_id,
            artifact_type=ArtifactType.OCR,
            content_text=ocr_text,
            file_path=str(ocr_file),
            model_name="imported",
            char_count=len(ocr_text)
        )
        repo.save_artifact(artifact)
        print(f"   ✅ 保存OCR产物")
    
    if report_text:
        artifact = Artifact(
            video_id=video_id,
            artifact_type=ArtifactType.REPORT,
            content_text=report_text,
            file_path=str(report_file),
            model_name="imported",
            char_count=len(report_text)
        )
        repo.save_artifact(artifact)
        print(f"   ✅ 保存AI报告产物")
    
    # 提取标签
    tags = extract_tags_from_text(report_text)
    if tags:
        repo.save_tags(video_id, tags, source='auto', confidence=0.8)
        print(f"   ✅ 保存标签: {', '.join(tags[:5])}{'...' if len(tags) > 5 else ''}")
    
    # 提取主题
    topics = extract_topics_from_text(report_text)
    if topics:
        topic_objects = []
        for t in topics:
            topic = Topic(
                video_id=video_id,
                title=t['title'],
                start_time=t['start_time'],
                end_time=t['end_time'],
                summary=t['summary'],
                keywords=[]
            )
            topic_objects.append(topic)
        
        repo.save_topics(video_id, topic_objects)
        print(f"   ✅ 保存主题: {len(topics)} 个章节")
    
    # 更新全文搜索索引
    repo.update_fts_index(video_id)
    print(f"   ✅ 更新全文搜索索引")
    
    return video_id


def test_search(repo):
    """测试搜索功能"""
    from db import SearchRepository
    
    print(f"\n{'='*60}")
    print("🔍 测试搜索功能")
    print(f"{'='*60}")
    
    search_repo = SearchRepository()
    
    # 测试1: 全文搜索
    print("\n1️⃣ 全文搜索 'INTP':")
    results = search_repo.search("INTP", limit=5)
    for i, r in enumerate(results, 1):
        print(f"   [{i}] {r.video_title} - {r.source_field} - 相关性: {r.relevance_score:.2f}")
        print(f"       片段: {r.matched_snippet[:80]}...")
    
    # 测试2: 按标签搜索
    print("\n2️⃣ 按标签搜索:")
    popular_tags = search_repo.get_popular_tags(limit=5)
    if popular_tags:
        print(f"   热门标签: {', '.join([t['name'] for t in popular_tags])}")
        
        tag_name = popular_tags[0]['name']
        results = search_repo.search_by_tags([tag_name], match_all=False, limit=3)
        print(f"\n   搜索标签 '{tag_name}' 的视频:")
        for i, r in enumerate(results, 1):
            tags_str = r['tags'] if isinstance(r['tags'], str) else ', '.join(r.get('tags', []))
            print(f"   [{i}] {r['title']} - 标签: {tags_str[:50]}...")
    else:
        print("   暂无标签")
    
    # 测试3: 搜索主题
    print("\n3️⃣ 搜索主题 '目标':")
    results = search_repo.search_topics("目标", limit=5)
    if results:
        for i, r in enumerate(results, 1):
            print(f"   [{i}] {r['title']} - 视频: {r['video_title']}")
    else:
        print("   未找到相关主题")


def main():
    """主函数"""
    print("╔════════════════════════════════════════════════════════════╗")
    print("║        数据库导入测试 - 使用真实 output 数据              ║")
    print("╚════════════════════════════════════════════════════════════╝")
    
    output_dir = Path("/Users/catherina/Documents/GitHub/knowledge/output")
    
    # 要导入的目录列表（选择有完整数据的）
    target_dirs = [
        "INTP：你不是迷茫，而是在逃避真正的目标_bilibili_BV1ngCyBiEkc_20251212_000338",
        "INFJ_·_INFP_·_INTP_·_INTJ：四种灵魂，四种爱情理想_大赏析_bilibili_BV12uUPBkEsZ_20251212_010216",
        "【干货】随身携带核武器的应用与风险！_bilibili_BV1tmKozuEJ9_20251212_003402",
        "test_20251211_214039",
    ]
    
    imported_ids = []
    
    for dir_name in target_dirs:
        session_dir = output_dir / dir_name
        if session_dir.exists() and session_dir.is_dir():
            video_id = import_directory(session_dir)
            if video_id:
                imported_ids.append(video_id)
        else:
            print(f"\n⚠️  目录不存在: {dir_name}")
    
    # 显示导入统计
    print(f"\n{'='*60}")
    print(f"📊 导入完成")
    print(f"{'='*60}")
    print(f"   成功导入: {len(imported_ids)} 个视频")
    print(f"   视频ID: {', '.join(map(str, imported_ids))}")
    
    # 测试搜索
    if imported_ids:
        repo = VideoRepository()
        test_search(repo)
    
    print(f"\n{'='*60}")
    print("✅ 测试完成！")
    print(f"{'='*60}")
    print("\n💡 后续操作:")
    print("   • 查看所有视频: make db-list")
    print("   • 全文搜索: make search Q=\"INTP\"")
    print("   • 按标签搜索: make search-tags TAGS=\"标签名\"")
    print("   • 查看数据库状态: make db-status")


if __name__ == "__main__":
    main()
