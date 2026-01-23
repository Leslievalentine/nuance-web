-- =============================================
-- Nuance Data Engine Schema v1.0 (IELTS Edition)
-- =============================================

-- 1. 单词表 (The Dispatcher)
-- 核心作用：存储单词基础信息，并决定该单词走哪个分析引擎
DROP TABLE IF EXISTS words CASCADE;
CREATE TABLE words (
    id SERIAL PRIMARY KEY,
    spelling TEXT NOT NULL UNIQUE,       -- 单词拼写
    phonetic TEXT,                       -- 音标
    definition_cn TEXT,                  -- 中文释义 (展示用)
    exchange TEXT,                       -- 词形变化串 (用于后续还原: d:thought/p:thought...)
    
    -- 📊 词频数据 (用于分级)
    bnc_rank INTEGER DEFAULT 0,          -- 英国国家语料库排名 (Classical)
    frq_rank INTEGER DEFAULT 0,          -- COCA 语料库排名 (Modern US)
    
    -- 🚦 核心调度字段 (Phase 1 重点)
    linguistic_class VARCHAR(20),        -- 语言学分类: 'CONTENT'(实义) / 'FUNCTION'(功能)
    processing_strategy VARCHAR(20),     -- 处理策略: 'PATTERN'(构式) / 'LINEAR'(线性) / 'PHRASAL'(短语) / 'BASIC'(基础)
    
    -- 🏷️ 筛选标记
    tags TEXT                            -- 原始标签 (zk/gk/ielts...)
);

-- 索引：加速查询与分流
CREATE INDEX idx_words_spelling ON words(spelling);
CREATE INDEX idx_words_strategy ON words(processing_strategy);
CREATE INDEX idx_words_rank ON words(bnc_rank, frq_rank);

-- 2. 语料库句子表 (The Raw Material)
-- 核心作用：存储原始例句与来源分类，不进行合并，保留原汁原味
DROP TABLE IF EXISTS corpus_sentences CASCADE;
CREATE TABLE corpus_sentences (
    id SERIAL PRIMARY KEY,
    sentence_text TEXT NOT NULL,         -- 句子原文
    words_array TEXT[] NOT NULL,         -- 分词数组 (用于 GIN 倒排索引)
    
    -- 🌍 来源元数据
    source_corpus VARCHAR(10),           -- 'BNC' 或 'MASC'
    original_genre VARCHAR(50),          -- 原始分类 (如 'World Affairs', 'twitter')
    file_id VARCHAR(100),                -- 来源文件名 (用于溯源)
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- GIN 索引：支持 array 包含查询 (words_array @> ARRAY['think'])
CREATE INDEX idx_corpus_words ON corpus_sentences USING GIN (words_array);
CREATE INDEX idx_corpus_source_genre ON corpus_sentences(source_corpus, original_genre);
