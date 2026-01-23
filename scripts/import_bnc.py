import os
import psycopg2
import re
from glob import glob
import xml.etree.ElementTree as ET

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BNC_PATH = os.path.join(BASE_DIR, 'data', 'BNC', 'Texts')

DB_CONFIG = {
    "dbname": "nuance_engine_db", "user": "postgres", "password": "5432", 
    "host": "localhost", "options": "-c client_encoding=utf8"
}

# BNC 分类代码映射表 (Codes -> Readable Genres)
GENRE_MAP = {
    'WRIDOM1': 'Literature', 
    'WRIDOM2': 'Natural Sci', 
    'WRIDOM3': 'Applied Sci',
    'WRIDOM4': 'Social Sci', 
    'WRIDOM5': 'World Affairs', 
    'WRIDOM6': 'Commerce',
    'WRIDOM7': 'Arts', 
    'WRIDOM8': 'Belief', 
    'WRIDOM9': 'Leisure',
    'ALLTYP3': 'Spoken (Demographic)',
    'ALLTYP4': 'Spoken (Context)'
}

def robust_extract_genre(filepath):
    """
    暴力且鲁棒的分类提取：不解析 XML 树结构，直接读取文件头 5KB 文本，
    正则搜索分类代码。这是处理 BNC 结构不一致最有效的方法。
    """
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            # 只读头部，分类信息通常在前 2000 字符内
            head = f.read(5000)
            
        # 1. 优先匹配书面语域 (WRIDOM)
        # 查找 target="WRIDOMx" 或者 直接出现 WRIDOMx
        match = re.search(r'(WRIDOM\d)', head)
        if match:
            code = match.group(1)
            return GENRE_MAP.get(code, 'Written (Misc)')
            
        # 2. 匹配口语语域 (ALLTYP)
        match_spoken = re.search(r'(ALLTYP\d)', head)
        if match_spoken:
            code = match_spoken.group(1)
            return GENRE_MAP.get(code, 'Spoken (Misc)')
            
        return 'Unclassified'
        
    except Exception:
        return 'Unclassified'

def parse_sentences(filepath):
    """
    解析句子：仍然使用 XML 解析，保证句子完整性
    """
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
        sents = []
        # 查找所有 <s> 标签
        for s in root.findall('.//s'):
            # 提取其中的 <w> (word) 和 <c> (punctuation)
            parts = []
            for node in s.iter():
                if node.tag in ('w', 'c', 'mw') and node.text:
                    parts.append(node.text.strip())
            
            if parts:
                text = " ".join(parts)
                # 过滤太短的碎片
                if len(parts) > 3:
                    # 简单分词数组 (用于索引)
                    words_arr = [w.lower() for w in parts if w.isalnum()]
                    if words_arr:
                        sents.append((text, words_arr))
        return sents
    except:
        return []

def run_import():
    print("🚑 [Fix Phase] 开始修复 BNC 数据...")
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # 1. 清理旧 BNC 数据
    print("🧹 正再清除旧的 BNC 错误数据...")
    cur.execute("DELETE FROM corpus_sentences WHERE source_corpus = 'BNC'")
    conn.commit()
    print("✅ 清理完成。")

    # 2. 重新导入
    files = glob(os.path.join(BNC_PATH, '**', '*.xml'), recursive=True)
    print(f"📚 重新扫描 {len(files)} 个文件...")
    
    buffer = []
    total_saved = 0
    
    for i, fpath in enumerate(files):
        fid = os.path.basename(fpath)
        
        # 提取分类 (使用新逻辑)
        real_genre = robust_extract_genre(fpath)
        
        # 提取句子
        sents = parse_sentences(fpath)
        
        for text, words_arr in sents:
            buffer.append((text, words_arr, 'BNC', real_genre, fid))
            
        # 批量写入
        if len(buffer) >= 2000:
            args = ','.join(cur.mogrify("(%s,%s,%s,%s,%s)", x).decode('utf-8') for x in buffer)
            cur.execute(f"INSERT INTO corpus_sentences (sentence_text, words_array, source_corpus, original_genre, file_id) VALUES {args}")
            conn.commit()
            total_saved += len(buffer)
            buffer = []
            print(f"\r⏳ 修复进度: {i}/{len(files)} | 当前: {real_genre.ljust(15)} | 已存: {total_saved}", end="")

    # 尾部处理
    if buffer:
        args = ','.join(cur.mogrify("(%s,%s,%s,%s,%s)", x).decode('utf-8') for x in buffer)
        cur.execute(f"INSERT INTO corpus_sentences (sentence_text, words_array, source_corpus, original_genre, file_id) VALUES {args}")
        conn.commit()

    print(f"\n🎉 BNC 数据修复完成！Unclassified 比例应大幅下降。")
    cur.close(); conn.close()

if __name__ == "__main__":
    run_import()
