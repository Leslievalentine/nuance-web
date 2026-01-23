import psycopg2
import os

# --- 配置 ---
DB_CONFIG = {
    "dbname": "nuance_engine_db", "user": "postgres", "password": "5432", 
    "host": "localhost", "options": "-c client_encoding=utf8"
}

def add_profile_table():
    print("🚧 [Schema Update] 正在创建结果表...")
    
    sql = """
    -- 3. 辨析结果表 (The Output)
    -- 存储最终计算出的 JSON 报告
    CREATE TABLE IF NOT EXISTS word_nuance_profiles (
        id SERIAL PRIMARY KEY,
        word_id INTEGER REFERENCES words(id) ON DELETE CASCADE,
        
        -- 📊 语域雷达 (Academic/Spoken/etc)
        register_stats JSONB DEFAULT '{}',
        
        -- 🧠 深度分析数据 (根据引擎不同，结构不同)
        -- Engine A: {"patterns": [...]}
        -- Engine B: {"modifiers": [...], "objects": [...]}
        analysis_data JSONB DEFAULT '{}',
        
        -- 📝 状态标记
        is_analyzed BOOLEAN DEFAULT FALSE,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        
        UNIQUE(word_id)
    );
    
    -- 索引
    CREATE INDEX IF NOT EXISTS idx_profiles_word ON word_nuance_profiles(word_id);
    """
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute(sql)
        conn.commit()
        print("✅ 成功创建 word_nuance_profiles 表！")
        cur.close(); conn.close()
    except Exception as e:
        print(f"❌ 错误: {e}")

if __name__ == "__main__":
    add_profile_table()
