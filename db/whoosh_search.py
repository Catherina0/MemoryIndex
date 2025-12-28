"""
Whoosh + jieba 全文搜索模块
替代 LIKE 方案，提供更好的中文分词和拼写纠错支持
"""

import os
import shutil
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

# Whoosh 相关
try:
    from whoosh.index import create_in, open_dir, exists_in
    from whoosh.fields import Schema, TEXT, ID, NUMERIC, STORED
    from whoosh.qparser import QueryParser, MultifieldParser
    from whoosh.query import FuzzyTerm, Or, And
    from whoosh import scoring
    WHOOSH_AVAILABLE = True
except ImportError:
    WHOOSH_AVAILABLE = False

# jieba 中文分词
try:
    from jieba.analyse import ChineseAnalyzer
    JIEBA_AVAILABLE = True
except ImportError:
    JIEBA_AVAILABLE = False


@dataclass
class WhooshSearchResult:
    """Whoosh 搜索结果"""
    video_id: int
    title: str
    content: str
    source: str
    relevance_score: float
    highlights: Optional[str] = None


class WhooshSearchIndex:
    """
    Whoosh 全文搜索索引管理
    
    特点:
    - 使用 jieba 中文分词
    - 支持 Fuzzy 模糊搜索
    - 支持 N-gram 拼写纠错
    - 高效的索引查询
    """
    
    DEFAULT_INDEX_DIR = "storage/whoosh_index"
    
    def __init__(self, index_dir: Optional[str] = None, db_path: Optional[str] = None):
        """
        初始化 Whoosh 索引
        
        Args:
            index_dir: 索引存储目录
            db_path: 数据库路径（暂未使用，保留接口兼容）
        """
        self.index_dir = index_dir or self.DEFAULT_INDEX_DIR
        self.db_path = db_path  # 保存数据库路径
        self.ix = None
        self._check_dependencies()
        
        if WHOOSH_AVAILABLE and JIEBA_AVAILABLE:
            self._init_schema()
    
    def _check_dependencies(self):
        """检查依赖是否安装"""
        if not WHOOSH_AVAILABLE:
            print("⚠️  Whoosh 未安装，请运行: pip install Whoosh")
        if not JIEBA_AVAILABLE:
            print("⚠️  jieba 未安装，请运行: pip install jieba")
    
    @property
    def is_available(self) -> bool:
        """检查是否可用"""
        return WHOOSH_AVAILABLE and JIEBA_AVAILABLE
    
    def _init_schema(self):
        """初始化索引 Schema"""
        # 使用 jieba 中文分词器
        analyzer = ChineseAnalyzer()
        
        self.schema = Schema(
            # 唯一标识
            doc_id=ID(stored=True, unique=True),
            video_id=ID(stored=True),
            
            # 可搜索字段（使用中文分词）
            title=TEXT(stored=True, analyzer=analyzer),
            content=TEXT(stored=True, analyzer=analyzer),
            
            # 元数据
            source=ID(stored=True),  # report, transcript, ocr, topic
            
            # 用于排序
            rank=NUMERIC(stored=True, sortable=True)
        )
    
    def init_index(self, force: bool = False) -> bool:
        """
        初始化索引目录
        
        Args:
            force: 是否强制重建索引
            
        Returns:
            是否成功
        """
        if not self.is_available:
            print("❌ Whoosh/jieba 未安装，无法初始化索引")
            return False
        
        try:
            # 如果目录存在且需要强制重建
            if force and os.path.exists(self.index_dir):
                shutil.rmtree(self.index_dir)
                print(f"🗑️  已删除旧索引: {self.index_dir}")
            
            # 创建目录
            if not os.path.exists(self.index_dir):
                os.makedirs(self.index_dir)
            
            # 创建或打开索引
            if exists_in(self.index_dir):
                self.ix = open_dir(self.index_dir)
                print(f"📂 已打开索引: {self.index_dir}")
            else:
                self.ix = create_in(self.index_dir, self.schema)
                print(f"✅ 已创建索引: {self.index_dir}")
            
            return True
            
        except Exception as e:
            print(f"❌ 初始化索引失败: {e}")
            return False
    
    def _ensure_index(self):
        """确保索引已初始化"""
        if self.ix is None:
            if exists_in(self.index_dir):
                self.ix = open_dir(self.index_dir)
            else:
                self.init_index()
    
    def add_document(self, 
                     video_id: int,
                     title: str,
                     content: str,
                     source: str,
                     doc_id: Optional[str] = None) -> bool:
        """
        添加单个文档到索引
        
        Args:
            video_id: 视频ID
            title: 标题
            content: 内容
            source: 来源类型（report/transcript/ocr/topic）
            doc_id: 文档唯一ID（默认自动生成）
            
        Returns:
            是否成功
        """
        if not self.is_available:
            return False
        
        self._ensure_index()
        
        try:
            # 生成文档ID
            if doc_id is None:
                doc_id = f"{video_id}_{source}_{hash(content[:100])}"
            
            writer = self.ix.writer()
            writer.add_document(
                doc_id=doc_id,
                video_id=str(video_id),
                title=title,
                content=content,
                source=source,
                rank=0
            )
            writer.commit()
            return True
            
        except Exception as e:
            print(f"❌ 添加文档失败: {e}")
            return False
    
    def add_documents(self, docs: List[Dict[str, Any]]) -> int:
        """
        批量添加文档到索引
        
        Args:
            docs: 文档列表，每个文档包含:
                  - video_id: int
                  - title: str
                  - content: str
                  - source: str
                  
        Returns:
            成功添加的文档数
        """
        if not self.is_available:
            return 0
        
        self._ensure_index()
        
        added = 0
        try:
            writer = self.ix.writer()
            
            for doc in docs:
                try:
                    doc_id = f"{doc['video_id']}_{doc['source']}_{hash(doc['content'][:100])}"
                    writer.add_document(
                        doc_id=doc_id,
                        video_id=str(doc['video_id']),
                        title=doc.get('title', ''),
                        content=doc.get('content', ''),
                        source=doc.get('source', 'unknown'),
                        rank=0
                    )
                    added += 1
                except Exception as e:
                    print(f"⚠️  跳过文档: {e}")
            
            writer.commit()
            print(f"✅ 已添加 {added} 个文档到索引")
            
        except Exception as e:
            print(f"❌ 批量添加失败: {e}")
        
        return added
    
    def search(self,
               query: str,
               fields: List[str] = None,
               limit: int = 20,
               fuzzy: bool = True,
               fuzzy_distance: int = 1) -> List[WhooshSearchResult]:
        """
        搜索文档
        
        Args:
            query: 搜索词
            fields: 搜索字段列表（默认 content）
            limit: 结果数量限制
            fuzzy: 是否启用模糊搜索
            fuzzy_distance: 模糊搜索允许的编辑距离（1-2）
            
        Returns:
            搜索结果列表
        """
        if not self.is_available or not query:
            return []
        
        self._ensure_index()
        
        if fields is None:
            fields = ['content', 'title']
        
        results = []
        
        try:
            with self.ix.searcher(weighting=scoring.BM25F()) as searcher:
                # 多字段搜索
                parser = MultifieldParser(fields, self.schema)
                
                # 构建查询
                if fuzzy and len(query) >= 2:
                    # 模糊搜索：query~1 表示允许1个字符差异
                    query_str = f"{query}~{fuzzy_distance}"
                else:
                    query_str = query
                
                try:
                    q = parser.parse(query_str)
                except Exception:
                    # 如果解析失败，尝试原始查询
                    q = parser.parse(query)
                
                # 执行搜索
                hits = searcher.search(q, limit=limit)
                
                for hit in hits:
                    results.append(WhooshSearchResult(
                        video_id=int(hit['video_id']),
                        title=hit['title'],
                        content=hit['content'][:300] if len(hit['content']) > 300 else hit['content'],
                        source=hit['source'],
                        relevance_score=round(hit.score, 3),
                        highlights=hit.highlights('content', top=3) if 'content' in hit else None
                    ))
                    
        except Exception as e:
            print(f"❌ 搜索失败: {e}")
        
        return results
    
    def search_with_fallback(self,
                             query: str,
                             fields: List[str] = None,
                             limit: int = 20) -> List[WhooshSearchResult]:
        """
        带回退的搜索：先精确搜索，结果不足则模糊搜索
        
        Args:
            query: 搜索词
            fields: 搜索字段
            limit: 结果限制
            
        Returns:
            搜索结果
        """
        # 第一次：精确搜索
        exact_results = self.search(query, fields=fields, limit=limit, fuzzy=False)
        
        if len(exact_results) >= limit // 2:
            return exact_results
        
        # 第二次：模糊搜索补充
        fuzzy_results = self.search(query, fields=fields, limit=limit * 2, fuzzy=True)
        
        # 合并去重
        seen_ids = {(r.video_id, r.source) for r in exact_results}
        combined = list(exact_results)
        
        for r in fuzzy_results:
            if (r.video_id, r.source) not in seen_ids:
                # 降低模糊匹配的分数权重
                r.relevance_score *= 0.8
                combined.append(r)
                seen_ids.add((r.video_id, r.source))
        
        # 按相关性排序
        combined.sort(key=lambda x: x.relevance_score, reverse=True)
        
        return combined[:limit]
    
    def update_document(self,
                        video_id: int,
                        source: str,
                        title: str,
                        content: str) -> bool:
        """
        更新文档（删除旧的，添加新的）
        
        Args:
            video_id: 视频ID
            source: 来源类型
            title: 新标题
            content: 新内容
            
        Returns:
            是否成功
        """
        if not self.is_available:
            return False
        
        self._ensure_index()
        
        try:
            writer = self.ix.writer()
            
            # 删除旧文档
            writer.delete_by_term('video_id', str(video_id))
            
            # 添加新文档
            doc_id = f"{video_id}_{source}_{hash(content[:100])}"
            writer.add_document(
                doc_id=doc_id,
                video_id=str(video_id),
                title=title,
                content=content,
                source=source,
                rank=0
            )
            
            writer.commit()
            return True
            
        except Exception as e:
            print(f"❌ 更新文档失败: {e}")
            return False
    
    def delete_video(self, video_id: int) -> bool:
        """
        删除视频的所有文档
        
        Args:
            video_id: 视频ID
            
        Returns:
            是否成功
        """
        if not self.is_available:
            return False
        
        self._ensure_index()
        
        try:
            writer = self.ix.writer()
            writer.delete_by_term('video_id', str(video_id))
            writer.commit()
            return True
        except Exception as e:
            print(f"❌ 删除失败: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """获取索引统计信息"""
        if not self.is_available:
            return {'available': False}
        
        self._ensure_index()
        
        try:
            with self.ix.searcher() as searcher:
                return {
                    'available': True,
                    'doc_count': searcher.doc_count(),
                    'index_dir': self.index_dir,
                    'fields': list(self.schema.names())
                }
        except Exception as e:
            return {'available': False, 'error': str(e)}
    
    def rebuild_from_sqlite(self, db_path: str = None) -> int:
        """
        从 SQLite 数据库重建索引
        
        Args:
            db_path: 数据库路径
            
        Returns:
            索引的文档数
        """
        if not self.is_available:
            return 0
        
        from .schema import get_connection
        
        # 强制重建索引
        self.init_index(force=True)
        
        conn = get_connection(db_path)
        
        try:
            # 获取所有 FTS 内容
            cursor = conn.execute("""
                SELECT 
                    f.video_id,
                    v.title,
                    f.content,
                    f.source_field as source
                FROM fts_content f
                JOIN videos v ON f.video_id = v.id
            """)
            
            docs = []
            for row in cursor.fetchall():
                docs.append({
                    'video_id': row['video_id'],
                    'title': row['title'],
                    'content': row['content'],
                    'source': row['source']
                })
            
            if docs:
                return self.add_documents(docs)
            return 0
            
        except Exception as e:
            print(f"❌ 重建索引失败: {e}")
            return 0
        finally:
            conn.close()


# 全局单例
_whoosh_index: Optional[WhooshSearchIndex] = None


def get_whoosh_index(db_path: Optional[str] = None) -> WhooshSearchIndex:
    """
    获取全局 Whoosh 索引实例
    
    Args:
        db_path: 数据库路径（可选，用于初始化）
    """
    global _whoosh_index
    if _whoosh_index is None:
        _whoosh_index = WhooshSearchIndex(db_path=db_path)
    return _whoosh_index


def check_whoosh_status() -> Dict[str, Any]:
    """检查 Whoosh 状态"""
    return {
        'whoosh_installed': WHOOSH_AVAILABLE,
        'jieba_installed': JIEBA_AVAILABLE,
        'ready': WHOOSH_AVAILABLE and JIEBA_AVAILABLE
    }


# 命令行入口
if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        
        if cmd == 'init':
            # 初始化索引
            idx = WhooshSearchIndex()
            force = '--force' in sys.argv
            if idx.init_index(force=force):
                print("✅ Whoosh 索引初始化完成")
            else:
                print("❌ 初始化失败")
                sys.exit(1)
                
        elif cmd == 'rebuild':
            # 从 SQLite 重建索引
            idx = WhooshSearchIndex()
            count = idx.rebuild_from_sqlite()
            print(f"✅ 已重建索引，共 {count} 个文档")
            
        elif cmd == 'status':
            # 显示状态
            status = check_whoosh_status()
            print(f"Whoosh 已安装: {'✅' if status['whoosh_installed'] else '❌'}")
            print(f"jieba 已安装: {'✅' if status['jieba_installed'] else '❌'}")
            
            if status['ready']:
                idx = get_whoosh_index()
                stats = idx.get_stats()
                print(f"索引目录: {stats.get('index_dir', 'N/A')}")
                print(f"文档数量: {stats.get('doc_count', 0)}")
            
        elif cmd == 'search':
            # 测试搜索
            if len(sys.argv) < 3:
                print("用法: python -m db.whoosh_search search <查询词>")
                sys.exit(1)
            
            query = sys.argv[2]
            idx = get_whoosh_index()
            idx._ensure_index()
            
            results = idx.search_with_fallback(query, limit=10)
            
            print(f"\n🔍 搜索: {query}")
            print(f"找到 {len(results)} 个结果:\n")
            
            for i, r in enumerate(results, 1):
                print(f"{i}. [ID={r.video_id}] {r.title[:50]}...")
                print(f"   来源: {r.source}, 相关性: {r.relevance_score}")
                print(f"   内容: {r.content[:80]}...")
                print()
        
        else:
            print(f"未知命令: {cmd}")
            print("可用命令: init, rebuild, status, search")
            sys.exit(1)
    else:
        print("Whoosh 搜索模块")
        print("用法:")
        print("  python -m db.whoosh_search init [--force]  # 初始化索引")
        print("  python -m db.whoosh_search rebuild         # 从数据库重建")
        print("  python -m db.whoosh_search status          # 查看状态")
        print("  python -m db.whoosh_search search <词>     # 测试搜索")
