import nltk
from nltk.corpus import wordnet as wn
from nltk.stem import WordNetLemmatizer
import psycopg2
import json

DB_CONFIG = {
    "dbname": "nuance_engine_db", "user": "postgres", "password": "5432", 
    "host": "localhost", "options": "-c client_encoding=utf8"
}

class SynonymEngine:
    def __init__(self):
        try: wn.synsets('test')
        except: nltk.download('wordnet'); nltk.download('omw-1.4')
        self.lemmatizer = WordNetLemmatizer()

    def get_db_connection(self):
        return psycopg2.connect(**DB_CONFIG)

    def get_synonyms_scored(self, target_word):
        """
        获取近义词并打分 (增强版：支持复数/变体)
        """
        # 1. 尝试直接查找
        target_synsets = wn.synsets(target_word)
        
        # 2. 如果没找到（例如 blocks），尝试还原原形 (block)
        if not target_synsets:
            lemma = self.lemmatizer.lemmatize(target_word)
            if lemma != target_word:
                target_synsets = wn.synsets(lemma)
        
        if not target_synsets: return []
        
        main_synset = target_synsets[0]
        candidates = {} 
        
        for syn in target_synsets:
            for lemma in syn.lemmas():
                w = lemma.name().replace('_', ' ').lower()
                # 排除自己 (包含单复数形式)
                if w == target_word.lower() or w == self.lemmatizer.lemmatize(target_word): 
                    continue
                
                cand_syns = wn.synsets(w)
                score = 0
                if cand_syns:
                    sim = main_synset.path_similarity(cand_syns[0])
                    if sim: score = sim
                
                if w not in candidates or score > candidates[w]:
                    candidates[w] = score

        if not candidates: return []

        # 3. 数据库验证
        conn = self.get_db_connection()
        cur = conn.cursor()
        cand_list = list(candidates.keys())
        
        sql = """
            SELECT w.id, w.spelling, w.definition_cn, w.bnc_rank
            FROM words w
            JOIN word_nuance_profiles p ON w.id = p.word_id
            WHERE w.spelling = ANY(%s) AND p.is_analyzed = TRUE
        """
        cur.execute(sql, (cand_list,))
        rows = cur.fetchall()
        conn.close()

        results = []
        for r in rows:
            sp = r[1]
            results.append({
                "id": r[0],
                "spelling": sp,
                "def": r[2],
                "rank": r[3],
                "score": candidates.get(sp, 0)
            })
            
        results.sort(key=lambda x: (x['score'], -x['rank']), reverse=True)
        return results

    def duel_words(self, word_a, word_b):
        # ... (Duel 逻辑保持不变，请确保不要删除这部分代码) ...
        conn = self.get_db_connection()
        cur = conn.cursor()
        sql = """
            SELECT w.spelling, p.register_stats, p.analysis_data, w.processing_strategy
            FROM words w
            JOIN word_nuance_profiles p ON w.id = p.word_id
            WHERE w.spelling IN (%s, %s)
        """
        cur.execute(sql, (word_a, word_b))
        rows = cur.fetchall()
        conn.close()
        if len(rows) < 2: return None
        data = {r[0]: {"stats": r[1], "analysis": r[2], "strategy": r[3]} for r in rows}
        return self._calculate_delta(data[word_a], data[word_b])

    def _calculate_delta(self, data_a, data_b):
        # ... (Duel 逻辑保持不变) ...
        report = {"register_contrast": {}, "collocation_contrast": {}}
        for source in ['BNC', 'MASC']:
            stats_a = data_a['stats'].get(source, {})
            stats_b = data_b['stats'].get(source, {})
            total_a = sum(stats_a.values()) or 1
            total_b = sum(stats_b.values()) or 1
            all_genres = set(stats_a.keys()) | set(stats_b.keys())
            diffs = []
            for g in all_genres:
                pct_a = (stats_a.get(g, 0) / total_a) * 100
                pct_b = (stats_b.get(g, 0) / total_b) * 100
                diffs.append({"genre": g, "a_pct": pct_a, "b_pct": pct_b, "delta": pct_a - pct_b})
            diffs.sort(key=lambda x: abs(x['delta']), reverse=True)
            report["register_contrast"][source] = diffs[:4]

        items_a = self._extract_core_items(data_a['analysis'], data_a['strategy'])
        items_b = self._extract_core_items(data_b['analysis'], data_b['strategy'])
        unique_a = items_a - items_b
        unique_b = items_b - items_a
        report["collocation_contrast"] = {"unique_a": list(unique_a)[:5], "unique_b": list(unique_b)[:5]}
        return report

    def _extract_core_items(self, analysis, strategy):
        # ... (Duel 逻辑保持不变) ...
        items = set()
        if strategy == 'LINEAR':
            for genre_data in analysis.values():
                for mod in genre_data.get('modifiers', []): items.add(mod['p'])
                for obj in genre_data.get('objects', []): items.add(obj['p'])
        elif strategy == 'PATTERN':
            for genre_data in analysis.values():
                for pat in genre_data: items.add(pat['template'])
        return items
