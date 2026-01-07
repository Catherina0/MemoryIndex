#!/usr/bin/env python3
"""
网页归档处理与数据库集成
类似 db_integration.py 的架构，用于网页内容
"""
import sys
import json
import hashlib
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from db import VideoRepository, SearchRepository
from db.models import (
    Video, Artifact, Topic, TimelineEntry,
    SourceType, ProcessingStatus, ArtifactType
)


def _generate_folder_name_with_llm_for_archive(
    archive_result: Dict[str, Any],
    original_folder: Path
) -> Optional[str]:
    """
    \u4f7f\u7528 llama-3.1-8b-instant \u6a21\u578b\u6839\u636e\u5f52\u6863\u5185\u5bb9\u751f\u6210\u7b80\u6d01\u7684\u6587\u4ef6\u5939\u540d\u79f0
    
    Args:
        archive_result: \u5f52\u6863\u7ed3\u679c\u5b57\u5178
        original_folder: \u539f\u59cb\u6587\u4ef6\u5939\u8def\u5f84
    
    Returns:
        \u751f\u6210\u7684\u6587\u4ef6\u5939\u540d\u79f0\uff08\u4e0d\u5305\u542b\u65f6\u95f4\u6233\uff09
    """
    import os
    try:
        from groq import Groq
    except ImportError:
        print("  \u26a0\ufe0f  Groq SDK \u672a\u5b89\u88c5\uff0c\u4f7f\u7528\u9ed8\u8ba4\u6587\u4ef6\u5939\u540d")
        return None
    
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("  \u26a0\ufe0f  GROQ_API_KEY \u672a\u8bbe\u7f6e\uff0c\u4f7f\u7528\u9ed8\u8ba4\u6587\u4ef6\u5939\u540d")
        return None
    
    try:
        # \u8bfb\u53d6\u5f52\u6863\u7684 README.md \u5185\u5bb9
        readme_path = Path(archive_result.get('markdown_path', ''))
        if not readme_path.exists():
            # \u5c1d\u8bd5\u67e5\u627e output_path \u4e0b\u7684 README.md
            output_path = Path(archive_result.get('output_path', ''))
            readme_path = output_path / 'README.md'
            if not readme_path.exists():
                print("  \u26a0\ufe0f  \u672a\u627e\u5230 README.md\uff0c\u4f7f\u7528\u9ed8\u8ba4\u6587\u4ef6\u5939\u540d")
                return None
        
        markdown_content = readme_path.read_text(encoding='utf-8')
        
        client = Groq(api_key=api_key)
        
        # \u63d0\u53d6\u5185\u5bb9\u6458\u8981
        content_lines = markdown_content.split('\\n')
        content_start = 0
        
        # \u8df3\u8fc7 YAML frontmatter
        if content_lines and content_lines[0].strip() == '---':
            for i, line in enumerate(content_lines[1:], 1):
                if line.strip() == '---':
                    content_start = i + 1
                    break
        
        # \u83b7\u53d6\u5b9e\u9645\u5185\u5bb9
        actual_content = '\\n'.join(content_lines[content_start:])
        # \u79fb\u9664\u56fe\u7247\u94fe\u63a5
        import re
        actual_content = re.sub(r'!\\[.*?\\]\\(.*?\\)', '', actual_content)
        # \u9650\u5236\u957f\u5ea6\u5230\u524d800\u5b57\u7b26
        content_summary = actual_content[:800].strip()
        
        if not content_summary or len(content_summary) < 20:
            print("  \u26a0\ufe0f  \u5185\u5bb9\u592a\u77ed\uff0c\u4f7f\u7528\u9ed8\u8ba4\u6587\u4ef6\u5939\u540d")
            return None
        
        title = archive_result.get('title', '\u672a\u547d\u540d')
        platform = archive_result.get('platform', 'web')
        url = archive_result.get('url', '')
        
        prompt = f"""\u6839\u636e\u4ee5\u4e0b\u7f51\u9875\u5185\u5bb9\uff0c\u751f\u6210\u4e00\u4e2a\u7b80\u6d01\u3001\u63cf\u8ff0\u6027\u7684\u6587\u4ef6\u5939\u540d\u79f0\u3002

\u7f51\u9875\u6807\u9898\uff1a{title}
\u5e73\u53f0\uff1a{platform}
URL\uff1a{url}

\u5185\u5bb9\u6458\u8981\uff1a
{content_summary}

\u8981\u6c42\uff1a
1. \u6587\u4ef6\u5939\u540d\u79f0\u5e94\u8be5\u7b80\u6d01\u660e\u4e86\uff0c\u80fd\u591f\u53cd\u6620\u5185\u5bb9\u7684\u6838\u5fc3\u4e3b\u9898
2. \u4f7f\u7528\u4e0b\u5212\u7ebf(_)\u5206\u9694\u5355\u8bcd\uff0c\u4e0d\u8981\u4f7f\u7528\u7a7a\u683c\u6216\u7279\u6b8a\u5b57\u7b26
3. \u957f\u5ea6\u4e0d\u8d85\u8fc730\u4e2a\u5b57\u7b26\uff08\u4e2d\u6587\u63092\u4e2a\u5b57\u7b26\u8ba1\u7b97\uff09
4. \u53ea\u8fd4\u56de\u6587\u4ef6\u5939\u540d\u79f0\uff0c\u4e0d\u8981\u6709\u4efb\u4f55\u89e3\u91ca\u6216\u6807\u70b9\u7b26\u53f7
5. \u4f7f\u7528\u4e2d\u6587\u6216\u82f1\u6587\u5747\u53ef\uff0c\u4f46\u8981\u786e\u4fdd\u6587\u4ef6\u7cfb\u7edf\u517c\u5bb9
6. \u4e0d\u9700\u8981\u5305\u542b\u5e73\u53f0\u540d\u79f0

\u793a\u4f8b\u683c\u5f0f\uff1a
- \u673a\u5668\u5b66\u4e60\u5165\u95e8\u6307\u5357
- Python\u6570\u636e\u5206\u6790\u6280\u5de7
- \u6df1\u5ea6\u5b66\u4e60\u56fe\u50cf\u5206\u7c7b

\u8bf7\u76f4\u63a5\u8fd4\u56de\u6587\u4ef6\u5939\u540d\u79f0\uff1a"""

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "\u4f60\u662f\u4e00\u4e2a\u6587\u4ef6\u547d\u540d\u52a9\u624b\uff0c\u64c5\u957f\u6839\u636e\u7f51\u9875\u5185\u5bb9\u751f\u6210\u7b80\u6d01\u3001\u63cf\u8ff0\u6027\u7684\u6587\u4ef6\u5939\u540d\u79f0\u3002"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=50,
            temperature=0.3,
        )
        
        folder_name = response.choices[0].message.content.strip()
        
        # 清理文件夹名称
        folder_name = re.sub(r'["\'\n\r\t]', '', folder_name)
        folder_name = re.sub(r'[/\\]', '_', folder_name)
        folder_name = re.sub(r'[<>:"|?*]', '', folder_name)
        
        # 限制长度
        if len(folder_name) > 50:
            folder_name = folder_name[:50]
        
        # \u5982\u679c\u751f\u6210\u5931\u8d25\u6216\u4e3a\u7a7a\uff0c\u8fd4\u56de None
        if not folder_name or len(folder_name) < 3:
            print("  \u26a0\ufe0f  LLM \u751f\u6210\u7684\u6587\u4ef6\u5939\u540d\u65e0\u6548")
            return None
        
        print(f"  \u2705 LLM \u751f\u6210\u7684\u6587\u4ef6\u5939\u540d: {folder_name}")
        return folder_name
        
    except Exception as e:
        print(f"  \u26a0\ufe0f  LLM \u6587\u4ef6\u5939\u547d\u540d\u5931\u8d25: {e}")
        return None


class ArchiveProcessor:
    """网页归档处理与数据库集成"""
    
    def __init__(self, db_path: Optional[str] = None):
        self.repo = VideoRepository(db_path)
    
    def process_and_save(
        self,
        url: str,
        output_dir: Path,
        archive_result: Dict[str, Any],
        source_type: str = 'web_archive',
        with_ocr: bool = False,
        processing_config: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        处理网页归档并保存到数据库
        
        Args:
            url: 网页URL
            output_dir: 输出目录
            archive_result: 归档结果字典（来自 UniversalArchiver.archive()）
            source_type: 来源类型（如 zhihu, xiaohongshu等）
            with_ocr: 是否进行OCR识别
            processing_config: 处理配置
        
        Returns:
            int: video_id（数据库主键，实际为通用内容ID）
        """
        if not archive_result.get('success'):
            raise ValueError(f"归档失败: {archive_result.get('error')}")
        
        # 1. 计算内容hash（基于URL+内容）
        content_for_hash = f"{url}_{archive_result.get('content', '')[:1000]}"
        content_hash = hashlib.sha256(content_for_hash.encode()).hexdigest()
        
        # 检查是否已存在
        existing = self.repo.get_video_by_hash(content_hash)
        if existing:
            print(f"⚠️  网页已存在（ID: {existing.id}），跳过处理")
            return existing.id
        
        # 2. 确定source_type枚举
        source_type_map = {
            'zhihu': SourceType.ZHIHU,
            'xiaohongshu': SourceType.XIAOHONGSHU,
            'bilibili': SourceType.BILIBILI,
            'twitter': SourceType.TWITTER,
            'reddit': SourceType.REDDIT,
            'web': SourceType.WEB_ARCHIVE,
        }
        source_enum = source_type_map.get(
            archive_result.get('platform', source_type).lower(),
            SourceType.WEB_ARCHIVE
        )
        
        # 3. 创建记录（使用Video表，但实际是网页内容）
        video = Video(
            content_hash=content_hash,
            video_id=url,  # 使用URL作为唯一标识
            source_type=source_enum,
            source_url=url,
            title=archive_result.get('title', '未命名网页'),
            platform_title=archive_result.get('title'),
            file_path=str(archive_result.get('output_path', '')),
            file_size_bytes=archive_result.get('content_length', 0),
            processing_config=processing_config or {
                'archive_mode': 'web',
                'with_ocr': with_ocr
            },
            status=ProcessingStatus.PROCESSING
        )
        
        try:
            db_id = self.repo.create_video(video)
            print(f"✅ 创建归档记录: ID={db_id}")
            
            # 4. 保存原始内容
            content_artifact = Artifact(
                video_id=db_id,
                artifact_type=ArtifactType.TRANSCRIPT,  # 复用transcript类型存储网页内容
                content_text=archive_result.get('content', ''),
                content_json={
                    'url': url,
                    'title': archive_result.get('title'),
                    'platform': archive_result.get('platform'),
                    'content_length': archive_result.get('content_length'),
                    'archive_time': datetime.now().isoformat()
                },
                file_path=str(archive_result.get('output_path', '')),
                model_name='crawl4ai' if 'crawl4ai' in str(archive_result) else 'drissionpage'
            )
            self.repo.save_artifact(content_artifact)
            print("✅ 保存归档内容")
            
            # 5. 如果有OCR，处理并保存
            if with_ocr and archive_result.get('output_path'):
                ocr_result = self._process_ocr_for_archive(
                    archive_result.get('output_path'),
                    output_dir
                )
                if ocr_result:
                    ocr_artifact = Artifact(
                        video_id=db_id,
                        artifact_type=ArtifactType.OCR,
                        content_text=self._extract_plain_text(ocr_result),
                        content_json=ocr_result,
                        file_path=str(output_dir / 'archive_ocr.json'),
                        model_name=ocr_result.get('engine', 'vision_ocr')
                    )
                    self.repo.save_artifact(ocr_artifact)
                    print("✅ 保存OCR结果")
            
            # 6. 生成AI报告（如果配置了GROQ_API_KEY）
            # 读取归档的Markdown内容（使用实际的output_dir，不是archive_result中的旧路径）
            archived_content = self._read_archived_content(str(output_dir))
            
            # 如果有OCR结果，合并到内容中
            if with_ocr and ocr_result:
                archived_content += f"\n\n## OCR识别文字\n\n{ocr_result['combined_text']}"
            
            print(f"  📝 内容长度: {len(archived_content)} 字符")
            
            report_data = self._generate_report_for_archive(
                archived_content,
                output_dir,
                with_ocr
            )
            if report_data:
                report_artifact = Artifact(
                    video_id=db_id,
                    artifact_type=ArtifactType.REPORT,
                    content_text=report_data.get('content', ''),
                    content_json=report_data,
                    file_path=str(output_dir / 'report.md'),
                    model_name=report_data.get('model', 'llama-3.3-70b')
                )
                self.repo.save_artifact(report_artifact)
                print("✅ 保存AI报告")
                
                # 7. 提取并保存标签
                tags = self._extract_tags(report_data)
                if tags:
                    self.repo.save_tags(db_id, tags, source='auto')
                    print(f"✅ 保存标签: {', '.join(tags)}")
                
                # 8. 提取并保存主题
                topics = self._extract_topics(report_data)
                if topics:
                    self.repo.save_topics(db_id, topics)
                    print(f"✅ 保存 {len(topics)} 个主题")
            
            # 9. 更新全文搜索索引
            self.repo.update_fts_index(db_id)
            print("✅ 更新搜索索引")
            
            # 10. 标记处理完成
            self.repo.update_video_status(db_id, ProcessingStatus.COMPLETED)
            print(f"🎉 归档处理完成: ID={db_id}")
            
            return db_id
            
        except Exception as e:
            # 标记失败
            if 'db_id' in locals():
                self.repo.update_video_status(
                    db_id,
                    ProcessingStatus.FAILED,
                    str(e)
                )
            print(f"❌ 处理失败: {e}")
            raise
    
    def _process_ocr_for_archive(
        self,
        markdown_path: str,
        output_dir: Path
    ) -> Optional[Dict]:
        """
        对归档的图片进行OCR识别
        扫描output_dir/images目录中的所有图片并进行OCR
        """
        try:
            from ocr.ocr_vision import init_vision_ocr, ocr_image_vision
        except ImportError:
            print("  ⚠️  OCR模块导入失败，跳过OCR识别")
            return None
        
        # 查找images目录
        images_dir = None
        
        # 尝试在output_dir中查找images目录
        for item in output_dir.iterdir():
            if item.is_dir():
                images_subdir = item / 'images'
                if images_subdir.exists() and images_subdir.is_dir():
                    images_dir = images_subdir
                    break
        
        if not images_dir or not images_dir.exists():
            print("  ℹ️  未找到images目录，跳过OCR识别")
            return None
        
        # 获取所有图片文件
        image_files = list(images_dir.glob('*.jpg')) + \
                     list(images_dir.glob('*.jpeg')) + \
                     list(images_dir.glob('*.png')) + \
                     list(images_dir.glob('*.webp'))
        
        if not image_files:
            print("  ℹ️  images目录为空，跳过OCR识别")
            return None
        
        print(f"  🔍 发现 {len(image_files)} 张图片，开始OCR识别...")
        
        # 初始化Vision OCR
        try:
            ocr_instance = init_vision_ocr()
        except Exception as e:
            print(f"  ⚠️  Vision OCR初始化失败: {e}")
            return None
        
        # 对每张图片进行OCR
        ocr_results = []
        for i, img_path in enumerate(image_files, 1):
            try:
                print(f"    处理图片 {i}/{len(image_files)}: {img_path.name}")
                text = ocr_image_vision(ocr_instance, str(img_path))
                if text and text.strip():
                    ocr_results.append({
                        'image': img_path.name,
                        'text': text.strip(),
                        'length': len(text.strip())
                    })
                    print(f"      ✓ 识别文字 {len(text.strip())} 字符")
                else:
                    print(f"      - 未识别到文字")
            except Exception as e:
                print(f"      ✗ OCR失败: {e}")
        
        if not ocr_results:
            print("  ℹ️  所有图片均未识别到文字")
            return None
        
        print(f"  ✅ OCR完成：{len(ocr_results)} 张图片识别出文字")
        
        return {
            'engine': 'vision_ocr',
            'total_images': len(image_files),
            'recognized_images': len(ocr_results),
            'results': ocr_results,
            'combined_text': '\n\n'.join([f"[{r['image']}]\n{r['text']}" for r in ocr_results])
        }
    
    def _generate_report_for_archive(
        self,
        content: str,
        output_dir: Path,
        with_ocr: bool = False
    ) -> Optional[Dict]:
        """
        使用AI生成网页内容报告
        调用与视频处理相同的LLM
        """
        import os
        try:
            from groq import Groq
        except ImportError:
            print("  ⚠️  Groq SDK 未安装，跳过AI报告生成")
            return None
        
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            print("  ⚠️  GROQ_API_KEY 未设置，跳过AI报告生成")
            return None
        
        try:
            client = Groq(api_key=api_key)
            model = os.getenv("GROQ_LLM_MODEL", "openai/gpt-oss-120b")
            max_tokens = int(os.getenv("GROQ_MAX_TOKENS", "8192"))
            temperature = float(os.getenv("GROQ_TEMPERATURE", "0.7"))
            
            prompt = f"""
请将以下网页内容整理成一份**结构化 Markdown 知识档案**。

**⚠️ 重要：识别错误修正**
- 网页可能存在排版问题或OCR识别错误
- 请主动识别并修正同音字/词错误，特别是专业术语
- 使用准确、专业的术语表达

你需要：
1. **使用 Markdown** 输出（标题、列表、引用、表格等）
2. 提取主要观点和核心内容
3. 自动识别"主题/章节"并结构化总结
4. 提取重要数据：数字、规则、引用、日期等
5. 生成标签和摘要：
   - **标签（tags）**：3-6个高度概括的主题标签，如"技术"、"教育"、"人文"等
   - **摘要**：不超过50个字的系统性内容概括

推荐结构：
## 摘要
（不超过50字的核心内容概括）

## 主要内容
## 关键观点
## 重要信息
## 标签
格式：标签: 标签1, 标签2, 标签3

以下是网页内容：
{content[:30000]}
"""

            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": """你是一个专业的内容整理助手，具备智能纠错能力。
                        你的任务是从网页内容中提取核心信息，生成结构化的知识档案。
                        确保输出使用准确、专业的术语表达。"""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=max_tokens,
                temperature=temperature,
            )
            
            report_content = response.choices[0].message.content
            
            # 保存报告到文件
            report_path = output_dir / 'report.md'
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            return {
                'content': report_content,
                'model': model,
                'tags': self._parse_tags_from_content(report_content),
                'topics': []  # TODO: 从报告中解析主题
            }
        except Exception as e:
            print(f"  ✗ AI报告生成失败: {e}")
            return None
    
    def _read_archived_content(self, output_path: str) -> str:
        """读取归档的Markdown内容"""
        if not output_path:
            return ""
        
        try:
            output_path_obj = Path(output_path)
            
            # 如果是目录，递归查找 README.md
            if output_path_obj.is_dir():
                # 先检查当前目录
                readme_path = output_path_obj / "README.md"
                if readme_path.exists():
                    with open(readme_path, 'r', encoding='utf-8') as f:
                        return f.read()
                
                # 查找子目录中的 README.md
                for readme in output_path_obj.rglob("README.md"):
                    try:
                        with open(readme, 'r', encoding='utf-8') as f:
                            return f.read()
                    except Exception:
                        continue
                
                print(f"  ⚠️  未找到 README.md 在: {output_path}")
            # 如果是文件，直接读取
            elif output_path_obj.is_file():
                with open(output_path_obj, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                print(f"  ⚠️  路径不存在: {output_path}")
        except Exception as e:
            print(f"  ⚠️  读取归档内容失败: {e}")
        
        return ""
    
    def _extract_plain_text(self, data: Dict) -> str:
        """从结构化数据提取纯文本"""
        if isinstance(data, dict):
            if 'combined_text' in data:
                return data['combined_text']
            elif 'text' in data:
                return data['text']
            elif 'content' in data:
                return data['content']
            return json.dumps(data, ensure_ascii=False)
        return str(data)
    
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
                start_time=None,  # 网页内容没有时间轴
                end_time=None,
                keywords=topic_data.get('keywords', []),
                key_points=topic_data.get('key_points', []),
                sequence=i
            )
            topics.append(topic)
        
        return topics
    
    def _parse_tags_from_content(self, content: str) -> list:
        """从报告内容中解析标签"""
        import re
        # 查找 "标签: xxx, xxx" 格式
        tag_match = re.search(r'标签[：:]\s*(.+)', content)
        if tag_match:
            tags_str = tag_match.group(1)
            tags = [tag.strip() for tag in re.split(r'[,，]', tags_str)]
            return [tag for tag in tags if tag and len(tag) < 20]
        return []


async def archive_and_save(
    url: str,
    output_dir: str = "output",
    with_ocr: bool = False,
    headless: bool = True
) -> int:
    """
    完整的归档流程：归档网页 → 生成报告 → 存入数据库
    
    Args:
        url: 网页URL
        output_dir: 输出目录
        with_ocr: 是否进行OCR识别
        headless: 是否使用无头模式
    
    Returns:
        int: 数据库记录ID
    """
    from archiver import UniversalArchiver
    
    # 1. 创建输出目录
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
    output_path = Path(output_dir) / f"archive_{url_hash}_{timestamp}"
    output_path.mkdir(parents=True, exist_ok=True)
    
    print(f"📂 输出目录: {output_path}")
    
    # 2. 执行网页归档
    print(f"\n🌐 开始归档: {url}")
    archiver = UniversalArchiver(
        output_dir=str(output_path),
        headless=headless,
        verbose=True
    )
    
    archive_result = await archiver.archive(url)
    
    if not archive_result.get('success'):
        raise Exception(f"归档失败: {archive_result.get('error')}")
    
    print(f"✅ 归档完成: {archive_result['output_path']}")
    
    # 3. 使用 LLM 重命名外层文件夹
    print(f"\n🤖 生成语义化文件夹名...")
    new_folder_name = _generate_folder_name_with_llm_for_archive(
        archive_result=archive_result,
        original_folder=output_path
    )
    
    if new_folder_name and new_folder_name != output_path.name:
        new_output_path = Path(output_dir) / f"{new_folder_name}_{timestamp}"
        try:
            # 如果目标文件夹已存在，添加后缀
            counter = 1
            temp_path = new_output_path
            while temp_path.exists():
                temp_path = Path(output_dir) / f"{new_folder_name}_{timestamp}_{counter}"
                counter += 1
            new_output_path = temp_path
            
            output_path.rename(new_output_path)
            output_path = new_output_path
            print(f"✅ 文件夹已重命名: {output_path.name}")
        except Exception as e:
            print(f"⚠️  文件夹重命名失败: {e}")
    
    # 4. 保存到数据库
    print(f"\n💾 保存到数据库...")
    processor = ArchiveProcessor()
    db_id = processor.process_and_save(
        url=url,
        output_dir=output_path,
        archive_result=archive_result,
        with_ocr=with_ocr,
        processing_config={
            'archive_mode': 'web',
            'with_ocr': with_ocr,
            'headless': headless
        }
    )
    
    print(f"\n{'='*60}")
    print(f"✅ 全部完成！")
    print(f"   📊 数据库ID: {db_id}")
    print(f"   📁 输出目录: {output_path}")
    print(f"   📄 报告文件: {output_path}/report.md")
    print(f"{'='*60}")
    
    return db_id


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='网页归档与数据库集成')
    parser.add_argument('url', help='网页URL')
    parser.add_argument('--output-dir', default='output', help='输出目录')
    parser.add_argument('--with-ocr', action='store_true', help='启用OCR识别')
    parser.add_argument('--visible', action='store_true', help='显示浏览器（调试）')
    
    args = parser.parse_args()
    
    # 运行异步归档
    db_id = asyncio.run(archive_and_save(
        url=args.url,
        output_dir=args.output_dir,
        with_ocr=args.with_ocr,
        headless=not args.visible
    ))
    
    print(f"\n🎉 归档成功！数据库ID: {db_id}")


if __name__ == '__main__':
    main()
