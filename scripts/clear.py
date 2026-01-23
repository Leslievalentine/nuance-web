import psycopg2
import os

DB_CONFIG = {
    "dbname": "nuance_engine_db", "user": "postgres", "password": "5432", 
    "host": "localhost", "options": "-c client_encoding=utf8"
}

def clear_profiles():
    print("🧹 正在清除分析结果 (Analysis Results)...")
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        # 仅清空分析结果，保留 words 和 corpus_sentences
        cur.execute("TRUNCATE TABLE word_nuance_profiles RESTART IDENTITY CASCADE;")
        conn.commit()
        print("✅ 已清空。请运行新的 main.py 进行重算。")
        conn.close()
    except Exception as e:
        print(f"❌ 错误: {e}")

if __name__ == "__main__":
    clear_profiles()
