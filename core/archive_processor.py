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
    使用 openai/gpt-oss-20b 模型根据归档内容生成简洁的文件夹名称
    
    Args:
        archive_result: 归档结果字典
        original_folder: 原始文件夹路径
    
    Returns:
        生成的文件夹名称（不包含时间戳）
    """
    import os
    try:
        from groq import Groq
    except ImportError:
        print("  ⚠️  Groq SDK 未安装，使用默认文件夹名")
        return None
    
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("  ⚠️  GROQ_API_KEY 未设置，使用默认文件夹名")
        return None
    
    try:
        # 读取归档的 README.md 内容
        readme_path = Path(archive_result.get('markdown_path', ''))
        if not readme_path.exists():
            # 尝试查找 output_path 下的 README.md
            output_path = Path(archive_result.get('output_path', ''))
            readme_path = output_path / 'README.md'
            if not readme_path.exists():
                print("  ⚠️  未找到 README.md，使用默认文件夹名")
                return None
        
        markdown_content = readme_path.read_text(encoding='utf-8')
        
        client = Groq(api_key=api_key)
        
        # 提取内容摘要
        content_lines = markdown_content.split('\\n')
        content_start = 0
        
        # 跳过 YAML frontmatter
        if content_lines and content_lines[0].strip() == '---':
            for i, line in enumerate(content_lines[1:], 1):
                if line.strip() == '---':
                    content_start = i + 1
                    break
        
        # 获取实际内容
        actual_content = '\\n'.join(content_lines[content_start:])
        # 移除图片链接
        import re
        actual_content = re.sub(r'!\[.*?\]\(.*?\)', '', actual_content)
        # 限制长度到前800字符
        content_summary = actual_content[:800].strip()
        
        if not content_summary or len(content_summary) < 20:
            print("  ⚠️  内容太短，使用默认文件夹名")
            return None
        
        title = archive_result.get('title', '未命名')
        platform = archive_result.get('platform', 'web')
        url = archive_result.get('url', '')
        
        # Build prompt without backslashes in f-string
        newline = '\n'
        prompt = f"""根据以下网页内容，生成一个简洁、描述性的文件夹名称。

网页标题：{title}
平台：{platform}
URL：{url}

内容摘要：
{content_summary}

要求：
1. 文件夹名称应该简洁明了，能够反映内容的核心主题
2. 使用下划线(_)分隔单词，不要使用空格或特殊字符
3. 长度不超过30个字符（中文按2个字符计算）
4. 只返回文件夹名称，不要有任何解释或标点符号
5. 使用中文或英文均可，但要确保文件系统兼容
6. 不需要包含平台名称

示例格式：
- 机器学习入门指南
- Python数据分析技巧
- 深度学习图像分类

请直接返回文件夹名称："""

        # 使用环境变量中的模型，如果未设置则使用默认的 Groq 模型
        model_name = os.getenv("GROQ_NAMING_MODEL", "llama-3.1-8b-instant")

        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "你是一个文件命名助手，擅长根据网页内容生成简洁、描述性的文件夹名称。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=60,
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
        
        # 如果生成失败或为空，返回 None
        if not folder_name or len(folder_name) < 3:
            print("  ⚠️  LLM 生成的文件夹名无效")
            return None
        
        print(f"  ✅ LLM 生成的文件夹名: {folder_name}")
        return folder_name
        
    except Exception as e:
        print(f"  ⚠️  LLM 文件夹命名失败: {e}")
        return None


class ArchiveProcessor:
    """网页归档处理与数据库集成"""
    
    # OSS-120b 模型限制
    MAX_CONTEXT_TOKENS = 131072  # 最大上下文窗口
    MAX_OUTPUT_TOKENS = 65536    # 最大输出 tokens
    LONG_TEXT_THRESHOLD = 100000  # 启动长文本模式的阈值
    
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
                    model_name=report_data.get('model', 'openai/gpt-oss-20b')
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
            
            # 9. 保存到 archived/ 文件夹（用于全文搜索）
            self._save_to_archived_folder(
                output_dir=output_dir,
                url=url,
                title=archive_result.get('title', '未命名网页'),
                platform=archive_result.get('platform', 'web')
            )
            
            # 10. 更新全文搜索索引
            self.repo.update_fts_index(db_id)
            print("✅ 更新搜索索引")
            
            # 11. 标记处理完成
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
    
    def _estimate_tokens(self, text: str) -> int:
        """
        估算文本的 token 数量
        使用简单规则：中文字符约1.5 tokens，英文单词约1 token
        """
        chinese_chars = len([c for c in text if '一' <= c <= '鿿'])
        other_chars = len(text) - chinese_chars
        # 粗略估算：中文 1.5 tokens/char，英文 4 chars/token
        return int(chinese_chars * 1.5 + other_chars / 4)
    
    def _split_content_by_tokens(self, content: str, max_tokens: int) -> list:
        """
        将内容按 token 限制分割成多个片段
        尽量保持段落完整性
        """
        paragraphs = content.split('\n\n')
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        for para in paragraphs:
            para_tokens = self._estimate_tokens(para)
            
            # 如果单个段落就超过限制，强制分割
            if para_tokens > max_tokens:
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                    current_chunk = []
                    current_tokens = 0
                
                # 按字符强制分割超长段落
                chars_per_token = len(para) / para_tokens if para_tokens > 0 else 1
                chunk_size = int(max_tokens * chars_per_token * 0.9)  # 保留10%余量
                for i in range(0, len(para), chunk_size):
                    chunks.append(para[i:i + chunk_size])
                continue
            
            # 如果加上当前段落会超过限制，保存当前chunk
            if current_tokens + para_tokens > max_tokens:
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                current_chunk = [para]
                current_tokens = para_tokens
            else:
                current_chunk.append(para)
                current_tokens += para_tokens
        
        # 保存最后一个chunk
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
        
        return chunks
    
    def _generate_report_for_archive(
        self,
        content: str,
        output_dir: Path,
        with_ocr: bool = False
    ) -> Optional[Dict]:
        """
        使用AI生成网页内容报告
        支持长文本分段处理
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
            
            # 估算 token 数量
            content_tokens = self._estimate_tokens(content)
            print(f"  📊 内容估算 tokens: {content_tokens:,}")
            
            # 如果超过阈值，启动长文本模式
            if content_tokens > self.LONG_TEXT_THRESHOLD:
                print(f"  🔄 启动长文本分段处理模式")
                return self._generate_report_long_text(
                    client, model, content, output_dir, 
                    max_tokens, temperature
                )
            
            # 短文本模式：直接处理
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
{content}
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
    
    def _generate_report_long_text(
        self,
        client,
        model: str,
        content: str,
        output_dir: Path,
        max_tokens: int,
        temperature: float
    ) -> Optional[Dict]:
        """
        长文本分段处理模式
        将内容分段，逐段生成报告，并将前一段的报告作为背景
        """
        # 分割内容（每段约 80,000 tokens，保留余量）
        chunks = self._split_content_by_tokens(content, 80000)
        print(f"  📄 分割为 {len(chunks)} 个片段")
        
        previous_summary = ""
        all_reports = []
        
        for i, chunk in enumerate(chunks, 1):
            chunk_tokens = self._estimate_tokens(chunk)
            print(f"\n  🔹 处理片段 {i}/{len(chunks)} ({chunk_tokens:,} tokens)...")
            
            # 构建提示词
            if previous_summary:
                context_info = f"""
**前文背景总结：**
{previous_summary}

---

"""
            else:
                context_info = ""
            
            last_segment_instruction = ""
            if i == len(chunks):
                last_segment_instruction = "6. **这是最后一部分**，请生成最终的标签和摘要"
            
            # Build the final section string outside f-string to avoid backslash issues
            newline = '\n'
            final_section = f"## 标签{newline}格式：标签: 标签1, 标签2, 标签3{newline}{newline}## 全文摘要{newline}（不超过100字的整体概括）" if i == len(chunks) else ""
            
            prompt = f"""{context_info}请将以下网页内容片段（第 {i}/{len(chunks)} 部分）整理成**结构化 Markdown 知识档案**。

**⚠️ 重要要求：**
1. 识别并修正同音字/词错误，使用准确专业的术语
2. 使用 Markdown 格式（标题、列表、引用、表格等）
3. 提取主要观点和核心内容
4. 识别主题/章节并结构化总结
5. 提取重要数据：数字、规则、引用、日期等
{last_segment_instruction}

推荐结构：
## 片段 {i} - 核心内容
（本片段的主要内容）

## 关键观点
## 重要信息
{final_section}

以下是内容片段：
{chunk}
"""

            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {
                            "role": "system",
                            "content": """你是一个专业的内容整理助手，具备智能纠错能力和上下文整合能力。
                            你的任务是处理长文本的片段，并结合前文背景生成连贯的知识档案。"""
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                
                segment_report = response.choices[0].message.content
                all_reports.append(f"\n\n---\n\n{segment_report}")
                
                # 提取本段的核心内容作为下一段的背景
                # 简单截取前500字符作为摘要
                lines = segment_report.split('\n')
                summary_lines = []
                char_count = 0
                for line in lines:
                    if char_count > 500:
                        break
                    summary_lines.append(line)
                    char_count += len(line)
                previous_summary = '\n'.join(summary_lines)
                
                print(f"  ✅ 片段 {i} 处理完成")
                
            except Exception as e:
                print(f"  ✗ 片段 {i} 处理失败: {e}")
                all_reports.append(f"\n\n---\n\n## 片段 {i}\n（处理失败：{e}）\n\n")
        
        # 合并所有报告
        final_report = f"""# 长文本知识档案

> 本文档由 {len(chunks)} 个片段分段处理生成
> 总计约 {self._estimate_tokens(content):,} tokens

{''.join(all_reports)}
"""
        
        # 保存报告到文件
        report_path = output_dir / 'report.md'
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(final_report)
        
        print(f"\n  ✅ 长文本报告生成完成")
        
        return {
            'content': final_report,
            'model': model,
            'tags': self._parse_tags_from_content(final_report),
            'topics': [],
            'segments': len(chunks)
        }
    
    def _read_archived_content(self, output_path: str) -> str:
        """读取归档的原始内容（从archive_raw.md）"""
        if not output_path:
            return ""
        
        try:
            output_path_obj = Path(output_path)
            
            # 如果是目录，查找 archive_raw.md
            if output_path_obj.is_dir():
                # 先检查当前目录
                archive_raw_path = output_path_obj / "archive_raw.md"
                if archive_raw_path.exists():
                    with open(archive_raw_path, 'r', encoding='utf-8') as f:
                        return f.read()
                
                # 查找子目录中的 archive_raw.md
                for archive_raw in output_path_obj.rglob("archive_raw.md"):
                    try:
                        with open(archive_raw, 'r', encoding='utf-8') as f:
                            return f.read()
                    except Exception:
                        continue
                
                # 兼容旧版本：如果找不到 archive_raw.md，尝试读取 README.md
                readme_path = output_path_obj / "README.md"
                if readme_path.exists():
                    print(f"  ⚠️  未找到 archive_raw.md，使用 README.md")
                    with open(readme_path, 'r', encoding='utf-8') as f:
                        return f.read()
                
                print(f"  ⚠️  未找到 archive_raw.md 或 README.md 在: {output_path}")
            # 如果是文件，直接读取
            elif output_path_obj.is_file():
                with open(output_path_obj, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                print(f"  ⚠️  路径不存在: {output_path}")
        except Exception as e:
            print(f"  ⚠️  读取归档内容失败: {e}")
        
        return ""
    
    def _save_to_archived_folder(
        self, 
        output_dir: Path,
        url: str,
        title: str,
        platform: str
    ) -> Optional[str]:
        """
        将归档的markdown保存到 archived/ 文件夹
        使用与archiver相同的命名规则
        
        Args:
            output_dir: 输出目录（包含archive_raw.md的文件夹）
            url: 原始URL
            title: 网页标题
            platform: 平台名称
        
        Returns:
            保存的文件路径，失败返回None
        """
        try:
            # 确定archived目录
            project_root = Path(__file__).parent.parent
            archived_dir = project_root / "archived"
            archived_dir.mkdir(exist_ok=True)
            
            # 查找archive_raw.md
            archive_raw_path = None
            if output_dir.is_dir():
                # 先检查当前目录
                temp_path = output_dir / "archive_raw.md"
                if temp_path.exists():
                    archive_raw_path = temp_path
                else:
                    # 查找子目录
                    for item in output_dir.rglob("archive_raw.md"):
                        archive_raw_path = item
                        break
            
            if not archive_raw_path or not archive_raw_path.exists():
                print(f"  ⚠️  未找到 archive_raw.md，跳过保存到 archived/")
                return None
            
            # 读取内容
            with open(archive_raw_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 生成文件名（与archiver保持一致）
            # 格式: platform_hash_timestamp.md
            url_hash = hashlib.md5(url.encode()).hexdigest()[:4]
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # 平台名称映射
            platform_map = {
                'twitter': 'twitter',
                'x.com': 'twitter',
                'zhihu': 'zhihu',
                'xiaohongshu': 'xhs',
                'bilibili': 'bilibili',
                'reddit': 'reddit'
            }
            platform_short = platform_map.get(platform.lower(), platform[:10].lower())
            
            filename = f"{platform_short}_{url_hash}_{timestamp}.md"
            archived_path = archived_dir / filename
            
            # 添加元信息头部
            archived_content = f"""---
title: {title}
url: {url}
platform: {platform}
archived_at: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
---

{content}
"""
            
            # 保存文件
            with open(archived_path, 'w', encoding='utf-8') as f:
                f.write(archived_content)
            
            print(f"✅ 保存到 archived/: {filename}")
            return str(archived_path)
            
        except Exception as e:
            print(f"  ⚠️  保存到 archived/ 失败: {e}")
            return None
    
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
    
    # archive-run 和 archive-ocr 都会生成 report
    archive_result = await archiver.archive(url, generate_report=True)
    
    if not archive_result.get('success'):
        error_msg = archive_result.get('error', '未知错误')
        if archive_result.get('blocked'):
            fix_cmds = archive_result.get('fix_commands', [])
            print(f"\n🔒 归档被拦截！页面要求登录或触发了安全验证。")
            print(f"   错误详情: {error_msg.splitlines()[0]}")
            print(f"\n   ━━━━ 解决方法 ━━━━")
            for i, cmd in enumerate(fix_cmds, 1):
                print(f"   {i}️⃣   {cmd}")
            print(f"   ━━━━━━━━━━━━━━━━━━\n")
        raise Exception(f"归档失败: {error_msg}")
    
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

    # 从输入中提取真实 URL（兼容小红书分享文本等含有前后缀的场景）
    import re as _re
    _url_match = _re.search(r'https?://\S+', args.url)
    if _url_match:
        actual_url = _url_match.group(0).rstrip('！!。，,')
        if actual_url != args.url:
            print(f"📎 从分享文本中提取 URL: {actual_url}")
    else:
        actual_url = args.url

    # 运行异步归档
    db_id = asyncio.run(archive_and_save(
        url=actual_url,
        output_dir=args.output_dir,
        with_ocr=args.with_ocr,
        headless=not args.visible
    ))
    
    print(f"\n🎉 归档成功！数据库ID: {db_id}")


if __name__ == '__main__':
    main()
