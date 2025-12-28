#!/usr/bin/env python3
"""
修复 FTS5 分词器问题
从 porter unicode61 改为 trigram，以更好支持中文搜索
"""
import sqlite3
from pathlib import Path

DB_PATH = Path("storage/database/knowledge.db")

def main():
    print("🔧 修复 FTS 分词器...")
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # 1. 备份现有数据
        print("📦 备份现有 FTS 数据...")
        cursor.execute("""
            CREATE TEMP TABLE fts_backup AS
            SELECT * FROM fts_content
        """)
        backup_count = cursor.execute("SELECT COUNT(*) FROM fts_backup").fetchone()[0]
        print(f"   已备份 {backup_count} 条记录")
        
        # 2. 删除旧表
        print("🗑️  删除旧 FTS 表...")
        cursor.execute("DROP TABLE IF EXISTS fts_content")
        
        # 3. 创建新表（使用 unicode61 分词）
        print("✨ 创建新 FTS 表（unicode61 分词器）...")
        cursor.execute("""
            CREATE VIRTUAL TABLE fts_content USING fts5(
                video_id UNINDEXED,
                source_field UNINDEXED,
                title,
                content,
                tags,
                tokenize = 'unicode61 remove_diacritics 0'
            )
        """)
        
        # 4. 恢复数据
        print("📥 恢复数据到新表...")
        cursor.execute("""
            INSERT INTO fts_content (video_id, source_field, title, content, tags)
            SELECT video_id, source_field, title, content, tags
            FROM fts_backup
        """)
        
        # 5. 验证
        restored_count = cursor.execute("SELECT COUNT(*) FROM fts_content").fetchone()[0]
        print(f"   已恢复 {restored_count} 条记录")
        
        # 6. 测试搜索
        print("\n🔍 测试搜索...")
        test_queries = ['美国', '斩杀线', '流浪汉']
        for query in test_queries:
            result = cursor.execute("""
                SELECT COUNT(DISTINCT video_id) as count
                FROM fts_content
                WHERE content MATCH ?
            """, (query,))
            count = result.fetchone()[0]
            print(f"   '{query}': 找到 {count} 个视频")
        
        conn.commit()
        print("\n✅ 修复完成！")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ 错误: {e}")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    main()
