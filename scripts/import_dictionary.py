import sqlite3
import psycopg2
import os
import re

# --- 配置 ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SQLITE_DB_PATH = os.path.join(BASE_DIR, 'data', 'ecdict.db')

# 您的数据库密码
DB_CONFIG = {
    "dbname": "nuance_engine_db", "user": "postgres", "password": "5432", 
    "host": "localhost", "options": "-c client_encoding=utf8"
}

# 正则：只允许纯字母和连字符
VALID_WORD_PATTERN = re.compile(r"^[a-zA-Z\-]+$")

def determine_strategy(bnc, frq, tags):
    """
    🚦 分流调度逻辑 (Dispatcher Logic)
    根据词频和标签决定该词走哪个引擎
    """
    # 1. 极高频词 -> PATTERN (构式引擎)
    # 逻辑：BNC 或 COCA 排名前 2000，通常是 think, take, way 这类结构词
    if (0 < bnc <= 2000) or (0 < frq <= 2000):
        return 'PATTERN'
    
    # 2. 短语动词依赖词 -> PHRASAL (短语引擎) - (暂时简单处理，后续可细化)
    # 如果是极短的小词(length<=4)且排名靠前，大概率是 get, go, up, down
    # (此处先简化，主要靠 rank 分流 PATTERN)
    
    # 3. 中频实义词 -> LINEAR (线性搭配引擎)
    # 绝大多数雅思实义词 (2000 - 15000)
    return 'LINEAR'

def import_dict():
    print(f"🚀 [Phase 1] 开始导入词典并建立分流策略...")
    
    # 1. 初始化 Postgres 表结构
    conn_pg = psycopg2.connect(**DB_CONFIG)
    cur_pg = conn_pg.cursor()
    schema_path = os.path.join(BASE_DIR, 'database', 'schema.sql')
    with open(schema_path, 'r', encoding='utf-8') as f:
        cur_pg.execute(f.read())
    conn_pg.commit()
    print("✅ 数据库 Schema 初始化完成。")

    # 2. 连接 SQLite 源
    if not os.path.exists(SQLITE_DB_PATH):
        print(f"❌ 找不到 {SQLITE_DB_PATH}")
        return
    conn_sqlite = sqlite3.connect(SQLITE_DB_PATH)
    cur_sqlite = conn_sqlite.cursor()

    print("🔍 正在扫描 ECDICT (加入 BNC/FRQ 双重过滤)...")
    # 查询关键字段
    cur_sqlite.execute("SELECT word, phonetic, translation, exchange, tag, collins, oxford, bnc, frq FROM stardict")

    batch = []
    count_valid = 0
    count_skipped = 0

    while True:
        rows = cur_sqlite.fetchmany(5000)
        if not rows: break

        for row in rows:
            word, phonetic, trans, exc, tag, collins, oxford, bnc, frq = row
            
            # --- 🛡️ 核心过滤逻辑 (The Filter) ---
            if not word or not trans: continue
            
            # 1. 格式清洗 (仅字母)
            if not VALID_WORD_PATTERN.match(word):
                count_skipped += 1; continue
                
            # 数据类型安全转换
            bnc = int(bnc) if bnc else 0
            frq = int(frq) if frq else 0
            collins = int(collins) if collins else 0
            oxford = int(oxford) if oxford else 0
            tag = tag if tag else ''

            # 2. 雅思/常用度过滤器 (Expanded Logic)
            is_valid_candidate = False
            
            if 'ielts' in tag: is_valid_candidate = True
            elif collins > 0: is_valid_candidate = True
            elif oxford == 1: is_valid_candidate = True
            elif 0 < bnc <= 20000: is_valid_candidate = True  # BNC 前2万
            elif 0 < frq <= 20000: is_valid_candidate = True  # COCA 前2万 (新增!)

            if not is_valid_candidate:
                count_skipped += 1; continue

            # --- 🚦 策略打标 ---
            strategy = determine_strategy(bnc, frq, tag)
            linguistic_class = 'FUNCTION' if strategy == 'PATTERN' else 'CONTENT'

            batch.append((
                word, phonetic, trans, exc, 
                bnc, frq, 
                linguistic_class, strategy, tag
            ))

        if batch:
            args_str = ','.join(cur_pg.mogrify("(%s,%s,%s,%s,%s,%s,%s,%s,%s)", x).decode('utf-8') for x in batch)
            cur_pg.execute(f"""
                INSERT INTO words 
                (spelling, phonetic, definition_cn, exchange, bnc_rank, frq_rank, linguistic_class, processing_strategy, tags)
                VALUES {args_str}
                ON CONFLICT (spelling) DO NOTHING
            """)
            conn_pg.commit()
            count_valid += len(batch)
            batch = []
            print(f"\r⏳ 已入库: {count_valid} | 过滤掉: {count_skipped}", end="")

    print(f"\n\n🎉 词典导入完成！共 {count_valid} 个高价值雅思/常用词。")
    cur_pg.close(); conn_pg.close()
    cur_sqlite.close(); conn_sqlite.close()

if __name__ == "__main__":
    import_dict()
