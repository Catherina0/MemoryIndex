#!/usr/bin/env python3
"""
视频处理完成后的数据库存储集成
修改 process_video.py 的存储逻辑，将结果落库
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from db import VideoRepository, SearchRepository
from db.models import (
    Video, Artifact, Topic, TimelineEntry,
    SourceType, ProcessingStatus, ArtifactType
)


class VideoProcessor:
    """视频处理与数据库集成"""
    
    def __init__(self, db_path: Optional[str] = None):
        self.repo = VideoRepository(db_path)
    
    def process_and_save(
        self,
        video_path: str,
        output_dir: Path,
        source_url: Optional[str] = None,
        source_type: str = 'local',
        video_id: Optional[str] = None,
        processing_config: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        处理视频并保存到数据库（完整流程）
        
        Args:
            video_path: 视频文件路径
            output_dir: 输出目录
            source_url: 来源URL
            source_type: 来源类型
            video_id: 平台视频ID
            processing_config: 处理配置
        
        Returns:
            int: video_id（数据库主键）
        """
        # 1. 计算 hash（去重）
        content_hash = self.repo.calculate_content_hash(video_path)
        
        # 检查是否已存在
        existing = self.repo.get_video_by_hash(content_hash)
        if existing:
            print(f"⚠️  视频已存在（ID: {existing.id}），跳过处理")
            return existing.id
        
        # 2. 创建视频记录
        video = Video(
            content_hash=content_hash,
            video_id=video_id,
            source_type=SourceType(source_type),
            source_url=source_url,
            title=Path(video_path).stem,  # 临时标题
            file_path=video_path,
            file_size_bytes=Path(video_path).stat().st_size,
            processing_config=processing_config,
            status=ProcessingStatus.PROCESSING
        )
        
        try:
            db_video_id = self.repo.create_video(video)
            print(f"✅ 创建视频记录: ID={db_video_id}")
            
            # 3. 执行视频处理（调用原有逻辑）
            # 这里是原 process_video.py 的处理流程
            transcript_data = self._process_transcript(video_path, output_dir)
            ocr_data = self._process_ocr(video_path, output_dir)
            report_data = self._generate_report(transcript_data, ocr_data, output_dir)
            
            # 4. 保存处理产物
            # 4.1 转写文本
            if transcript_data:
                transcript_artifact = Artifact(
                    video_id=db_video_id,
                    artifact_type=ArtifactType.TRANSCRIPT,
                    content_text=self._extract_plain_text(transcript_data),
                    content_json=transcript_data,
                    file_path=str(output_dir / 'transcript_raw.json'),
                    model_name='whisper-large-v3'
                )
                self.repo.save_artifact(transcript_artifact)
                print("✅ 保存转写文本")
            
            # 4.2 OCR文本
            if ocr_data:
                ocr_artifact = Artifact(
                    video_id=db_video_id,
                    artifact_type=ArtifactType.OCR,
                    content_text=self._extract_plain_text(ocr_data),
                    content_json=ocr_data,
                    file_path=str(output_dir / 'ocr_raw.json'),
                    model_name='paddleocr'
                )
                self.repo.save_artifact(ocr_artifact)
                print("✅ 保存OCR文本")
            
            # 4.3 最终报告
            if report_data:
                report_artifact = Artifact(
                    video_id=db_video_id,
                    artifact_type=ArtifactType.REPORT,
                    content_text=report_data.get('content', ''),
                    content_json=report_data,
                    file_path=str(output_dir / 'report.md'),
                    model_name='llama-3.3-70b'
                )
                self.repo.save_artifact(report_artifact)
                print("✅ 保存最终报告")
                
                # 更新视频标题
                if 'title' in report_data:
                    # TODO: 添加 update_video 方法
                    pass
            
            # 5. 保存标签
            tags = self._extract_tags(report_data)
            if tags:
                self.repo.save_tags(db_video_id, tags, source='auto')
                print(f"✅ 保存标签: {', '.join(tags)}")
            
            # 6. 保存主题
            topics = self._extract_topics(report_data)
            if topics:
                self.repo.save_topics(db_video_id, topics)
                print(f"✅ 保存 {len(topics)} 个主题")
            
            # 7. 保存时间线
            timeline = self._build_timeline(transcript_data, ocr_data, output_dir)
            if timeline:
                self.repo.save_timeline(db_video_id, timeline)
                print(f"✅ 保存 {len(timeline)} 个时间线条目")
            
            # 8. 更新全文搜索索引
            self.repo.update_fts_index(db_video_id)
            print("✅ 更新搜索索引")
            
            # 9. 标记处理完成
            self.repo.update_video_status(db_video_id, ProcessingStatus.COMPLETED)
            print(f"🎉 处理完成: video_id={db_video_id}")
            
            return db_video_id
            
        except Exception as e:
            # 标记失败
            self.repo.update_video_status(
                db_video_id, 
                ProcessingStatus.FAILED, 
                str(e)
            )
            print(f"❌ 处理失败: {e}")
            raise
    
    # 以下是辅助方法（需要根据实际处理逻辑实现）
    
    def _process_transcript(self, video_path: str, output_dir: Path) -> Dict:
        """执行语音转写（调用原有逻辑）"""
        # TODO: 调用 process_video.py 的转写逻辑
        # 返回格式: {'segments': [{'start': 0, 'end': 5, 'text': '...'}]}
        return {}
    
    def _process_ocr(self, video_path: str, output_dir: Path) -> Dict:
        """执行OCR识别（调用原有逻辑）"""
        # TODO: 调用 ocr_utils.py 的OCR逻辑
        return {}
    
    def _generate_report(self, transcript_data: Dict, ocr_data: Dict, output_dir: Path) -> Dict:
        """生成最终报告（调用原有逻辑）"""
        # TODO: 调用 LLM 生成报告
        # 返回格式: {'title': '...', 'content': '...', 'tags': [], 'topics': []}
        return {}
    
    def _extract_plain_text(self, data: Dict) -> str:
        """从结构化数据提取纯文本"""
        if 'segments' in data:
            # 转写数据
            return '\n'.join([seg['text'] for seg in data['segments']])
        elif 'frames' in data:
            # OCR数据
            return '\n'.join([frame.get('text', '') for frame in data['frames']])
        elif 'content' in data:
            # 报告数据
            return data['content']
        return json.dumps(data, ensure_ascii=False)
    
    def _extract_tags(self, report_data: Dict) -> list:
        """从报告中提取标签"""
        return report_data.get('tags', [])
    
    def _extract_topics(self, report_data: Dict) -> list:
        """从报告中提取主题"""
        topics_data = report_data.get('topics', [])
        topics = []
        
        for i, topic_data in enumerate(topics_data):
            topic = Topic(
                video_id=0,  # 稍后填充
                title=topic_data.get('title', ''),
                summary=topic_data.get('summary'),
                start_time=topic_data.get('start_time'),
                end_time=topic_data.get('end_time'),
                keywords=topic_data.get('keywords', []),
                key_points=topic_data.get('key_points', []),
                sequence=i
            )
            topics.append(topic)
        
        return topics
    
    def _build_timeline(self, transcript_data: Dict, ocr_data: Dict, output_dir: Path) -> list:
        """构建时间线（合并转写和OCR）"""
        timeline = []
        
        # 从转写数据提取
        if 'segments' in transcript_data:
            for seg in transcript_data['segments']:
                entry = TimelineEntry(
                    video_id=0,
                    timestamp_seconds=seg['start'],
                    transcript_text=seg['text']
                )
                timeline.append(entry)
        
        # 从OCR数据提取
        if 'frames' in ocr_data:
            for frame in ocr_data['frames']:
                entry = TimelineEntry(
                    video_id=0,
                    timestamp_seconds=frame.get('timestamp', 0),
                    frame_number=frame.get('frame_number'),
                    ocr_text=frame.get('text'),
                    frame_path=frame.get('frame_path')
                )
                timeline.append(entry)
        
        # 按时间排序
        timeline.sort(key=lambda x: x.timestamp_seconds)
        
        return timeline


# 使用示例
if __name__ == '__main__':
    """
    集成到 process_video.py 的方法：
    
    1. 在 process_video.py 的主函数末尾添加：
    
    from db_integration import VideoProcessor
    
    processor = VideoProcessor()
    video_id = processor.process_and_save(
        video_path=args.video,
        output_dir=output_dir,
        source_url=args.url,
        source_type='bilibili',
        video_id='BV1xxx',
        processing_config={'fps': args.fps, 'model': 'whisper-large-v3'}
    )
    
    print(f"数据库视频ID: {video_id}")
    """
    pass
