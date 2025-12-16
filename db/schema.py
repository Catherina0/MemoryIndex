"""
数据库初始化和连接管理
"""
import sqlite3
from pathlib import Path
from typing import Optional
import json


def _json_adapter(data):
    """将 Python 对象转换为 JSON 字符串"""
    return json.dumps(data, ensure_ascii=False)


def _json_converter(data):
    """将 JSON 字符串转换为 Python 对象"""
    return json.loads(data)


# 注册 JSON 类型转换器
sqlite3.register_adapter(dict, _json_adapter)
sqlite3.register_adapter(list, _json_adapter)
sqlite3.register_converter("JSON", _json_converter)


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """
    获取数据库连接
    
    Args:
        db_path: 数据库文件路径，默认为 storage/database/knowledge.db
    
    Returns:
        sqlite3.Connection: 数据库连接对象
    """
    if db_path is None:
        # 默认路径
        project_root = Path(__file__).parent.parent
        db_path = project_root / "storage" / "database" / "knowledge.db"
    
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 连接数据库，启用 JSON 支持和外键约束
    conn = sqlite3.connect(
        str(db_path),
        detect_types=sqlite3.PARSE_DECLTYPES,
        check_same_thread=False
    )
    
    # 配置连接
    conn.row_factory = sqlite3.Row  # 返回字典式行
    conn.execute("PRAGMA foreign_keys = ON")  # 启用外键
    conn.execute("PRAGMA journal_mode = WAL")  # 启用 WAL 模式提升并发
    
    return conn


def init_database(db_path: Optional[str] = None, force_recreate: bool = False):
    """
    初始化数据库（创建表、索引、触发器等）
    
    Args:
        db_path: 数据库文件路径
        force_recreate: 是否强制重建（会删除所有数据）
    """
    if db_path is None:
        project_root = Path(__file__).parent.parent
        db_path = project_root / "storage" / "database" / "knowledge.db"
    
    db_path = Path(db_path)
    
    # 如果强制重建，删除旧数据库
    if force_recreate and db_path.exists():
        db_path.unlink()
        print(f"🗑️  已删除旧数据库: {db_path}")
    
    # 读取 schema.sql
    schema_file = Path(__file__).parent / "schema.sql"
    with open(schema_file, 'r', encoding='utf-8') as f:
        schema_sql = f.read()
    
    # 执行建表语句
    conn = get_connection(str(db_path))
    try:
        # 分割并执行每个语句（SQLite executescript 不支持参数化）
        conn.executescript(schema_sql)
        conn.commit()
        
        print(f"✅ 数据库初始化成功: {db_path}")
        
        # 检查表是否创建成功
        cursor = conn.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """)
        tables = [row['name'] for row in cursor.fetchall()]
        print(f"📊 已创建 {len(tables)} 张表: {', '.join(tables)}")
        
        # 检查 FTS5 表
        cursor = conn.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name LIKE 'fts_%'
        """)
        fts_tables = [row['name'] for row in cursor.fetchall()]
        if fts_tables:
            print(f"🔍 全文搜索表: {', '.join(fts_tables)}")
        
    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
        raise
    finally:
        conn.close()


def check_database_health(db_path: Optional[str] = None) -> dict:
    """
    检查数据库健康状态
    
    Returns:
        dict: 包含统计信息的字典
    """
    conn = get_connection(db_path)
    try:
        stats = {}
        
        # 统计各表记录数
        tables = ['videos', 'artifacts', 'tags', 'topics', 'timeline_entries']
        for table in tables:
            cursor = conn.execute(f"SELECT COUNT(*) as count FROM {table}")
            stats[table] = cursor.fetchone()['count']
        
        # FTS 表统计
        try:
            cursor = conn.execute("SELECT COUNT(*) as count FROM fts_content")
            stats['fts_content'] = cursor.fetchone()['count']
        except:
            stats['fts_content'] = 0
        
        # 数据库文件大小
        if db_path:
            db_file = Path(db_path)
        else:
            project_root = Path(__file__).parent.parent
            db_file = project_root / "storage" / "database" / "knowledge.db"
        
        if db_file.exists():
            stats['db_size_mb'] = db_file.stat().st_size / 1024 / 1024
        
        return stats
        
    finally:
        conn.close()


if __name__ == '__main__':
    """命令行工具：初始化数据库"""
    import argparse
    
    parser = argparse.ArgumentParser(description='初始化知识库数据库')
    parser.add_argument('--db', type=str, help='数据库文件路径')
    parser.add_argument('--force', action='store_true', help='强制重建（删除所有数据）')
    parser.add_argument('--check', action='store_true', help='检查数据库健康状态')
    
    args = parser.parse_args()
    
    if args.check:
        stats = check_database_health(args.db)
        print("\n📊 数据库统计:")
        for key, value in stats.items():
            if key == 'db_size_mb':
                print(f"  {key}: {value:.2f} MB")
            else:
                print(f"  {key}: {value}")
    else:
        init_database(args.db, args.force)
