#!/usr/bin/env python3
"""
数据库功能测试脚本
"""
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from db import init_database, VideoRepository, SearchRepository
from db.models import (
    Video, Artifact, Topic, TimelineEntry,
    SourceType, ProcessingStatus, ArtifactType
)


def test_init_database():
    """测试数据库初始化"""
    print("\n" + "="*60)
    print("测试 1: 数据库初始化")
    print("="*60)
    
    # 初始化（不强制重建）
    init_database()
    
    # 检查健康状态
    from db.schema import check_database_health
    stats = check_database_health()
    
    print("\n📊 数据库统计:")
    for key, value in stats.items():
        if key == 'db_size_mb':
            print(f"  {key}: {value:.2f} MB")
        else:
            print(f"  {key}: {value}")
    
    print("\n✅ 数据库初始化测试通过")


def test_video_crud():
    """测试视频 CRUD 操作"""
    print("\n" + "="*60)
    print("测试 2: 视频 CRUD 操作")
    print("="*60)
    
    repo = VideoRepository()
    
    # 创建测试视频
    test_video = Video(
        content_hash='test_hash_' + datetime.now().strftime('%Y%m%d%H%M%S'),
        video_id='BV1test',
        source_type=SourceType.BILIBILI,
        source_url='https://bilibili.com/video/BV1test',
        platform_title='测试视频标题',
        title='测试视频',
        duration_seconds=300.5,
        file_path='/path/to/test_video.mp4',
        file_size_bytes=1024*1024*100,
        processing_config={'fps': 1, 'model': 'whisper-large-v3'},
        status=ProcessingStatus.PENDING
    )
    
    # 创建
    video_id = repo.create_video(test_video)
    print(f"\n✅ 创建视频: ID={video_id}")
    
    # 读取
    video = repo.get_video_by_id(video_id)
    print(f"✅ 读取视频: {video.title}")
    print(f"   来源: {video.source_type.value}")
    print(f"   时长: {video.duration_seconds}s")
    print(f"   状态: {video.status.value}")
    
    # 更新状态
    repo.update_video_status(video_id, ProcessingStatus.COMPLETED)
    print(f"✅ 更新状态: COMPLETED")
    
    # 验证更新
    updated_video = repo.get_video_by_id(video_id)
    assert updated_video.status == ProcessingStatus.COMPLETED
    print(f"✅ 验证更新: {updated_video.status.value}")
    
    return video_id


def test_artifacts(video_id: int):
    """测试产物保存"""
    print("\n" + "="*60)
    print("测试 3: 产物保存")
    print("="*60)
    
    repo = VideoRepository()
    
    # 保存转写文本
    transcript = Artifact(
        video_id=video_id,
        artifact_type=ArtifactType.TRANSCRIPT,
        content_text="这是一段测试转写文本。包含中文和 English mixed content.",
        content_json={
            'segments': [
                {'start': 0, 'end': 5, 'text': '这是一段测试转写文本。'},
                {'start': 5, 'end': 10, 'text': '包含中文和 English mixed content.'}
            ]
        },
        model_name='whisper-large-v3'
    )
    transcript_id = repo.save_artifact(transcript)
    print(f"✅ 保存转写: artifact_id={transcript_id}")
    
    # 保存 OCR 文本
    ocr = Artifact(
        video_id=video_id,
        artifact_type=ArtifactType.OCR,
        content_text="OCR识别的文字内容\n机器学习\n深度学习\n神经网络",
        content_json={
            'frames': [
                {'frame_number': 1, 'text': 'OCR识别的文字内容'},
                {'frame_number': 2, 'text': '机器学习'},
                {'frame_number': 3, 'text': '深度学习'},
                {'frame_number': 4, 'text': '神经网络'}
            ]
        },
        model_name='paddleocr'
    )
    ocr_id = repo.save_artifact(ocr)
    print(f"✅ 保存OCR: artifact_id={ocr_id}")
    
    # 保存报告
    report = Artifact(
        video_id=video_id,
        artifact_type=ArtifactType.REPORT,
        content_text="""# 测试视频报告

## 主要内容
这是一个关于机器学习和深度学习的视频。

## 关键点
- 神经网络基础
- 卷积神经网络（CNN）
- 循环神经网络（RNN）

## 总结
本视频系统介绍了深度学习的核心概念。
""",
        model_name='llama-3.3-70b'
    )
    report_id = repo.save_artifact(report)
    print(f"✅ 保存报告: artifact_id={report_id}")
    
    # 读取产物
    artifacts = repo.get_artifacts(video_id)
    print(f"\n📦 共保存 {len(artifacts)} 个产物:")
    for art in artifacts:
        print(f"  - {art.artifact_type.value}: {art.char_count} 字符")


def test_tags(video_id: int):
    """测试标签保存"""
    print("\n" + "="*60)
    print("测试 4: 标签保存")
    print("="*60)
    
    repo = VideoRepository()
    
    # 保存标签
    tags = ['机器学习', '深度学习', '人工智能', '教育', '科技']
    repo.save_tags(video_id, tags, source='auto', confidence=0.95)
    print(f"✅ 保存标签: {', '.join(tags)}")
    
    # 读取标签
    saved_tags = repo.get_video_tags(video_id)
    print(f"✅ 读取标签: {', '.join(saved_tags)}")
    
    assert set(tags) == set(saved_tags)
    print("✅ 标签验证通过")


def test_topics(video_id: int):
    """测试主题保存"""
    print("\n" + "="*60)
    print("测试 5: 主题保存")
    print("="*60)
    
    repo = VideoRepository()
    
    # 创建主题
    topics = [
        Topic(
            video_id=video_id,
            title='神经网络基础',
            summary='介绍神经网络的基本概念和结构',
            start_time=0.0,
            end_time=100.0,
            keywords=['神经网络', '感知机', '激活函数'],
            key_points=['神经元结构', '前向传播', '反向传播'],
            sequence=1
        ),
        Topic(
            video_id=video_id,
            title='卷积神经网络',
            summary='讲解CNN的原理和应用',
            start_time=100.0,
            end_time=200.0,
            keywords=['CNN', '卷积层', '池化层'],
            key_points=['卷积操作', '特征提取', '图像识别'],
            sequence=2
        ),
        Topic(
            video_id=video_id,
            title='循环神经网络',
            summary='介绍RNN和LSTM',
            start_time=200.0,
            end_time=300.0,
            keywords=['RNN', 'LSTM', '序列模型'],
            key_points=['时序数据', '记忆单元', '长短期记忆'],
            sequence=3
        )
    ]
    
    topic_ids = repo.save_topics(video_id, topics)
    print(f"✅ 保存主题: {len(topic_ids)} 个")
    
    # 读取主题
    saved_topics = repo.get_topics(video_id)
    print(f"\n📚 主题列表:")
    for topic in saved_topics:
        print(f"  [{topic.sequence}] {topic.title}")
        print(f"      时间: {topic.start_time}s - {topic.end_time}s")
        print(f"      关键词: {', '.join(topic.keywords)}")


def test_timeline(video_id: int):
    """测试时间线保存"""
    print("\n" + "="*60)
    print("测试 6: 时间线保存")
    print("="*60)
    
    repo = VideoRepository()
    
    # 创建时间线条目
    entries = [
        TimelineEntry(
            video_id=video_id,
            timestamp_seconds=0.0,
            frame_number=1,
            transcript_text='欢迎来到机器学习课程',
            ocr_text='机器学习',
            frame_path='frames/frame_00001.png'
        ),
        TimelineEntry(
            video_id=video_id,
            timestamp_seconds=5.0,
            frame_number=6,
            transcript_text='今天我们讲解神经网络',
            ocr_text='神经网络基础',
            frame_path='frames/frame_00006.png'
        ),
        TimelineEntry(
            video_id=video_id,
            timestamp_seconds=10.0,
            frame_number=11,
            transcript_text='首先介绍感知机模型',
            ocr_text='感知机',
            frame_path='frames/frame_00011.png'
        )
    ]
    
    entry_ids = repo.save_timeline(video_id, entries)
    print(f"✅ 保存时间线: {len(entry_ids)} 个条目")


def test_fts_index(video_id: int):
    """测试全文搜索索引"""
    print("\n" + "="*60)
    print("测试 7: 全文搜索索引")
    print("="*60)
    
    repo = VideoRepository()
    
    # 更新 FTS 索引
    repo.update_fts_index(video_id)
    print("✅ 更新 FTS 索引")


def test_search():
    """测试搜索功能"""
    print("\n" + "="*60)
    print("测试 8: 搜索功能")
    print("="*60)
    
    search_repo = SearchRepository()
    
    # 全文搜索
    print("\n1️⃣ 全文搜索: '机器学习'")
    results = search_repo.search(query='机器学习', limit=5)
    print(f"   找到 {len(results)} 个结果")
    for i, result in enumerate(results, 1):
        print(f"   [{i}] {result.video_title}")
        print(f"       来源: {result.source_field}")
        print(f"       片段: {result.matched_snippet[:50]}...")
        print(f"       相关性: {result.relevance_score:.3f}")
    
    # 按标签搜索
    print("\n2️⃣ 按标签搜索: ['机器学习', '深度学习']")
    videos = search_repo.search_by_tags(tags=['机器学习', '深度学习'], match_all=True)
    print(f"   找到 {len(videos)} 个视频")
    for i, video in enumerate(videos[:3], 1):
        print(f"   [{i}] {video['title']}")
        print(f"       标签: {video.get('tags', '-')}")
    
    # 搜索主题
    print("\n3️⃣ 搜索主题: '神经网络'")
    topics = search_repo.search_topics(query='神经网络')
    print(f"   找到 {len(topics)} 个主题")
    for i, topic in enumerate(topics[:3], 1):
        print(f"   [{i}] {topic['title']}")
        print(f"       视频: {topic['video_title']}")
    
    # 热门标签
    print("\n4️⃣ 热门标签")
    tags = search_repo.get_popular_tags(limit=10)
    print(f"   Top {len(tags)} 标签:")
    for i, tag in enumerate(tags, 1):
        print(f"   [{i}] {tag['name']}: {tag['video_count']} 个视频")
    
    # 标签自动补全
    print("\n5️⃣ 标签自动补全: '机器'")
    suggestions = search_repo.suggest_tags(prefix='机器')
    print(f"   建议: {', '.join(suggestions)}")


def main():
    """运行所有测试"""
    print("🚀 开始数据库功能测试\n")
    
    try:
        # 1. 初始化数据库
        test_init_database()
        
        # 2. 测试视频 CRUD
        video_id = test_video_crud()
        
        # 3. 测试产物
        test_artifacts(video_id)
        
        # 4. 测试标签
        test_tags(video_id)
        
        # 5. 测试主题
        test_topics(video_id)
        
        # 6. 测试时间线
        test_timeline(video_id)
        
        # 7. 测试 FTS 索引
        test_fts_index(video_id)
        
        # 8. 测试搜索
        test_search()
        
        print("\n" + "="*60)
        print("🎉 所有测试通过！")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
