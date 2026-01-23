import os
import psycopg2
from glob import glob

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MASC_PATH = os.path.join(BASE_DIR, 'data', 'MASC', 'data')

DB_CONFIG = {
    "dbname": "nuance_engine_db", "user": "postgres", "password": "5432", 
    "host": "localhost", "options": "-c client_encoding=utf8"
}

def get_masc_genre(filepath):
    """
    通过父文件夹名获取分类 (例如 .../data/written/twitter/abc.txt -> twitter)
    """
    try:
        # 获取文件所在的目录名
        dirname = os.path.basename(os.path.dirname(filepath))
        # 如果直接在 written/spoken 下，可能要向上找一级，这里假设 MASC 结构标准
        return dirname
    except:
        return 'Unclassified'

def clean_masc_text(text):
    # MASC 尤其 twitter 包含大量垃圾字符，做最基础清洗
    # 替换掉非打印字符
    return text.replace('\x00', '').strip()

def import_masc():
    print("🇺🇸 [MASC] 开始导入现代/网络语料...")
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    files = glob(os.path.join(MASC_PATH, '**', '*.txt'), recursive=True)
    print(f"📚 发现 {len(files)} 个 TXT 文件")
    
    buffer = []
    total_saved = 0
    
    for i, fpath in enumerate(files):
        fid = os.path.basename(fpath)
        if fid.startswith('.'): continue # 忽略隐藏文件
        
        genre = get_masc_genre(fpath)
        
        try:
            with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            # MASC 没有 XML 标签，我们按换行符简单分句
            # 忽略过短的行
            lines = [clean_masc_text(l) for l in content.split('\n') if len(l.split()) > 3]
            
            for line in lines:
                words_arr = [w.lower() for w in line.split() if w.isalnum()]
                if not words_arr: continue
                
                buffer.append((line, words_arr, 'MASC', genre, fid))
                
            if len(buffer) >= 2000:
                args = ','.join(cur.mogrify("(%s,%s,%s,%s,%s)", x).decode('utf-8') for x in buffer)
                cur.execute(f"INSERT INTO corpus_sentences (sentence_text, words_array, source_corpus, original_genre, file_id) VALUES {args}")
                conn.commit()
                total_saved += len(buffer)
                buffer = []
                print(f"\r⏳ MASC 进度: {i}/{len(files)} | 已存: {total_saved}", end="")
                
        except Exception as e:
            print(f"⚠️ 跳过 {fid}: {e}")

    if buffer:
        args = ','.join(cur.mogrify("(%s,%s,%s,%s,%s)", x).decode('utf-8') for x in buffer)
        cur.execute(f"INSERT INTO corpus_sentences (sentence_text, words_array, source_corpus, original_genre, file_id) VALUES {args}")
        conn.commit()

    print(f"\n✅ MASC 导入完成。")
    cur.close(); conn.close()

if __name__ == "__main__":
    import_masc()
