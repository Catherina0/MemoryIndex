-- ============================================
-- 知识库数据库 Schema (SQLite)
-- ============================================

-- 1. 视频元信息表
CREATE TABLE IF NOT EXISTS videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- 唯一标识
    content_hash TEXT NOT NULL UNIQUE,      -- 视频文件的 SHA256 hash
    video_id TEXT,                          -- 平台视频ID（如 BV1xxx）
    
    -- 来源信息
    source_type TEXT NOT NULL,              -- 'local' | 'youtube' | 'bilibili' | 'twitter' | 'xiaohongshu' | 'douyin'
    source_url TEXT,                        -- 原始URL
    platform_title TEXT,                    -- 平台原始标题
    
    -- 视频属性
    title TEXT NOT NULL,                    -- 标准化标题
    duration_seconds REAL,                  -- 时长（秒）
    file_path TEXT NOT NULL,                -- 原视频存储路径
    file_size_bytes INTEGER,                -- 文件大小
    
    -- 处理配置
    processing_config JSON,                 -- 处理参数（fps、模型版本等）
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,                 -- 处理完成时间
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 状态管理
    status TEXT DEFAULT 'pending',          -- 'pending' | 'processing' | 'completed' | 'failed'
    error_message TEXT
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_videos_source ON videos(source_type, video_id);
CREATE INDEX IF NOT EXISTS idx_videos_status ON videos(status);
CREATE INDEX IF NOT EXISTS idx_videos_created ON videos(created_at DESC);


-- 2. 产物表（转写、OCR、报告）
CREATE TABLE IF NOT EXISTS artifacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id INTEGER NOT NULL,
    
    -- 产物类型
    artifact_type TEXT NOT NULL,            -- 'transcript' | 'ocr' | 'report'
    
    -- 内容
    content_text TEXT NOT NULL,             -- 纯文本内容（用于搜索）
    content_json JSON,                      -- 结构化内容（带时间戳等）
    
    -- 元信息
    file_path TEXT,                         -- 原文件路径
    model_name TEXT,                        -- 使用的模型（如 whisper-large-v3）
    model_params JSON,                      -- 模型参数
    
    -- 统计
    char_count INTEGER,                     -- 字符数
    word_count INTEGER,                     -- 词数
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_artifacts_video ON artifacts(video_id, artifact_type);
CREATE INDEX IF NOT EXISTS idx_artifacts_type ON artifacts(artifact_type);


-- 3. 标签表
CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE,  -- 标签名（忽略大小写）
    category TEXT,                              -- 标签分类（如 'topic', 'person', 'event'）
    count INTEGER DEFAULT 0,                    -- 使用次数（冗余，便于排序）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tags_name ON tags(name);
CREATE INDEX IF NOT EXISTS idx_tags_count ON tags(count DESC);


-- 4. 视频-标签关联表（多对多）
CREATE TABLE IF NOT EXISTS video_tags (
    video_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    
    -- 标签来源
    source TEXT,                            -- 'auto' | 'manual'
    confidence REAL,                        -- 自动标签的置信度（0-1）
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (video_id, tag_id),
    FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_video_tags_tag ON video_tags(tag_id);


-- 5. 主题/章节表
CREATE TABLE IF NOT EXISTS topics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id INTEGER NOT NULL,
    
    -- 主题信息
    title TEXT NOT NULL,                    -- 主题标题
    summary TEXT,                           -- 主题摘要
    
    -- 时间范围
    start_time REAL,                        -- 开始时间（秒）
    end_time REAL,                          -- 结束时间（秒）
    
    -- 关键信息
    keywords JSON,                          -- 关键词列表 ["keyword1", "keyword2"]
    key_points JSON,                        -- 要点列表
    
    -- 顺序
    sequence INTEGER,                       -- 章节顺序
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_topics_video ON topics(video_id, sequence);


-- 6. 时间线表（OCR/转写的时间对齐）
CREATE TABLE IF NOT EXISTS timeline_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id INTEGER NOT NULL,
    
    -- 时间信息
    timestamp_seconds REAL NOT NULL,        -- 时间点（秒）
    frame_number INTEGER,                   -- 帧号
    
    -- 内容
    transcript_text TEXT,                   -- 该时间点的转写文本
    ocr_text TEXT,                          -- 该时间点的OCR文本
    frame_path TEXT,                        -- 帧图片路径
    
    -- 元信息
    is_key_frame BOOLEAN DEFAULT 0,         -- 是否关键帧
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_timeline_video_time ON timeline_entries(video_id, timestamp_seconds);


-- 7. 全文搜索表（FTS5）
-- 主搜索表：合并所有文本内容
CREATE VIRTUAL TABLE IF NOT EXISTS fts_content USING fts5(
    video_id UNINDEXED,                     -- 不索引的ID字段
    source_field UNINDEXED,                 -- 来源字段（'report' | 'transcript' | 'ocr' | 'topic'）
    title,                                  -- 视频标题（高权重）
    content,                                -- 主要内容
    tags,                                   -- 标签（空格分隔）
    tokenize = 'unicode61 remove_diacritics 0'  -- Unicode分词（对中文支持较好）
);

-- FTS5 辅助表：存储文档长度等统计信息（自动生成）


-- 8. 嵌入向量表（预留，未来扩展）
CREATE TABLE IF NOT EXISTS embeddings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id INTEGER NOT NULL,
    artifact_type TEXT NOT NULL,            -- 'transcript' | 'report' | 'topic'
    chunk_index INTEGER,                    -- 分块索引
    
    -- 向量数据
    embedding_blob BLOB,                    -- 向量数据（序列化）
    embedding_model TEXT,                   -- 模型名称（如 'text-embedding-3-small'）
    
    -- 关联信息
    text_snippet TEXT,                      -- 对应文本片段
    start_time REAL,
    end_time REAL,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_embeddings_video ON embeddings(video_id, artifact_type);


-- 9. 处理日志表（可选，用于调试和审计）
CREATE TABLE IF NOT EXISTS processing_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id INTEGER,
    
    -- 处理步骤
    step_name TEXT NOT NULL,                -- 'download' | 'extract_audio' | 'asr' | 'ocr' | 'llm'
    status TEXT NOT NULL,                   -- 'started' | 'completed' | 'failed'
    
    -- 详细信息
    details JSON,                           -- 步骤详情
    duration_seconds REAL,                  -- 耗时
    error_message TEXT,
    
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_logs_video ON processing_logs(video_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_logs_step ON processing_logs(step_name, status);


-- ============================================
-- 触发器：自动更新统计
-- ============================================

-- 更新 videos.updated_at
CREATE TRIGGER IF NOT EXISTS update_video_timestamp 
AFTER UPDATE ON videos
BEGIN
    UPDATE videos SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- 更新标签使用计数
CREATE TRIGGER IF NOT EXISTS increment_tag_count
AFTER INSERT ON video_tags
BEGIN
    UPDATE tags SET count = count + 1 WHERE id = NEW.tag_id;
END;

CREATE TRIGGER IF NOT EXISTS decrement_tag_count
AFTER DELETE ON video_tags
BEGIN
    UPDATE tags SET count = count - 1 WHERE id = OLD.tag_id;
END;


-- ============================================
-- 视图：常用查询
-- ============================================

-- 视频完整信息视图
CREATE VIEW IF NOT EXISTS v_videos_full AS
SELECT 
    v.id,
    v.content_hash,
    v.title,
    v.source_type,
    v.source_url,
    v.duration_seconds,
    v.file_path,
    v.status,
    v.created_at,
    v.processed_at,
    
    -- 聚合标签
    GROUP_CONCAT(t.name, ', ') as tags,
    
    -- 统计信息
    COUNT(DISTINCT ar.id) as artifact_count,
    COUNT(DISTINCT tp.id) as topic_count
    
FROM videos v
LEFT JOIN video_tags vt ON v.id = vt.video_id
LEFT JOIN tags t ON vt.tag_id = t.id
LEFT JOIN artifacts ar ON v.id = ar.video_id
LEFT JOIN topics tp ON v.id = tp.id
GROUP BY v.id;


-- ============================================
-- 初始化数据
-- ============================================

-- 插入默认标签分类
INSERT OR IGNORE INTO tags (name, category) VALUES 
    ('教育', 'category'),
    ('科技', 'category'),
    ('娱乐', 'category'),
    ('新闻', 'category');
