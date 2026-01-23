import nltk
import psycopg2
from collections import Counter, defaultdict
import re

# NLTK 资源
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('taggers/averaged_perceptron_tagger')
except LookupError:
    nltk.download('punkt')
    nltk.download('averaged_perceptron_tagger')

DB_CONFIG = {
    "dbname": "nuance_engine_db", "user": "postgres", "password": "5432", 
    "host": "localhost", "options": "-c client_encoding=utf8"
}

class NuanceAnalyzer:
    def __init__(self):
        # 1. 黑名单语域 (不专业/噪音大)
        self.GENRE_BLACKLIST = {'spam', 'jokes', 'twitter', 'Unclassified'}
        
        # 2. 停用词
        self.stopwords = {
            'the','a','an','and','or','but','is','are','was','were','be','been',
            'this','that','it','he','she','they','we','i','you','my','your',
            'in','on','at','to','for','of','with','by'
        }
        
        # 3. 加载词形表
        self.lemma_map = self._load_lemma_map()
        self.MIN_SENTENCE_THRESHOLD = 5

    def _load_lemma_map(self):
        print("🧠 Loading Lemmatization Map...")
        lemma_db = {}
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cur = conn.cursor()
            cur.execute("SELECT spelling, exchange FROM words WHERE exchange IS NOT NULL AND exchange != ''")
            for base, exc in cur.fetchall():
                base = base.lower()
                variants = re.findall(r':[a-zA-Z\-]+', exc)
                for v in variants:
                    lemma_db[v[1:].lower()] = base
            conn.close()
            return lemma_db
        except: return {}

    def normalize_word(self, word):
        return self.lemma_map.get(word.lower(), word.lower())

    def analyze(self, target_word, strategy, sentences_data):
        target_lemma = target_word.lower()
        
        # 1. 双源语域雷达 (Dual-Source Radar)
        # 结构: {"BNC": {"Arts": 10}, "MASC": {"blog": 20}}
        register_stats = {"BNC": Counter(), "MASC": Counter()}
        grouped_sents = defaultdict(list) # 按语域分组例句
        
        for text, words_arr, source, genre in sentences_data:
            # A. 噪音清洗
            if genre in self.GENRE_BLACKLIST: continue
            if text.isupper(): continue # 过滤全大写标题 (LEAVING A LEGACY)
            if len(words_arr) < 4: continue
            
            # B. 统计分布
            # 确保 source 只有 BNC/MASC，防止脏数据
            src_key = source if source in ['BNC', 'MASC'] else 'Other'
            register_stats[src_key][genre] += 1
            
            # C. 收集例句用于深度分析
            grouped_sents[genre].append((text, words_arr))

        # 2. 策略分流
        analysis_result = {}
        
        # 获取 Top 5 活跃语域 (合并 BNC 和 MASC 的所有语域按总数排序)
        all_genres = Counter()
        for src in register_stats:
            all_genres.update(register_stats[src])
        
        top_genres = [g for g, c in all_genres.most_common(5)]
        
        if strategy == 'PATTERN':
            analysis_result = self._engine_a_pattern(target_lemma, top_genres, grouped_sents)
        elif strategy == 'LINEAR':
            analysis_result = self._engine_b_linear(target_lemma, top_genres, grouped_sents)
            
        return {
            "register": {k: dict(v) for k, v in register_stats.items()}, # 转为普通dict
            "analysis": analysis_result
        }

    # ==========================================================
    # 🟠 Engine A: 构式解析 (升级版: 词性感知)
    # ==========================================================
    def _engine_a_pattern(self, target_lemma, genres, grouped_sents):
        patterns_by_genre = {}
        
        for genre in genres:
            sents = grouped_sents[genre]
            if len(sents) < self.MIN_SENTENCE_THRESHOLD: continue
            
            pattern_counter = Counter()
            examples_map = defaultdict(list)
            
            for text, words_arr in sents:
                try:
                    tagged = nltk.pos_tag(words_arr)
                    
                    # 寻找目标词，且必须进行词性检查
                    indices = [i for i, (w, t) in enumerate(tagged) 
                               if self.normalize_word(w) == target_lemma]
                    
                    for idx in indices:
                        target_tag = tagged[idx][1]
                        
                        # 🔥 核心修正: 根据目标词性分流
                        pat = None
                        if target_tag.startswith('V'): # 动词
                            pat = self._extract_verb_pattern(tagged, idx)
                        elif target_tag.startswith('N'): # 名词
                            pat = self._extract_noun_pattern(tagged, idx)
                        elif target_tag.startswith('J'): # 形容词
                            pat = self._extract_adj_pattern(tagged, idx)
                            
                        if pat:
                            pattern_counter[pat] += 1
                            if len(examples_map[pat]) < 3:
                                examples_map[pat].append(text)
                except: continue
            
            # 整理结果
            top_patterns = []
            for pat, count in pattern_counter.most_common(5):
                if count < 2: continue
                top_patterns.append({
                    "template": pat,
                    "count": count,
                    "examples": examples_map[pat]
                })
            
            if top_patterns:
                patterns_by_genre[genre] = top_patterns
                
        return patterns_by_genre

    def _extract_verb_pattern(self, tagged, idx):
        if idx + 1 >= len(tagged): return None
        next_w, next_t = tagged[idx+1]
        
        if next_w == 'that': return "V + that-clause"
        if next_t == 'TO': return "V + to do"
        if next_t == 'IN': return f"V + {next_w} + n."
        # 排除代词主格，防止从句误判为宾语
        if (next_t.startswith('N') or next_t.startswith('P')) and next_w not in ['i','he','she','we','they']:
            return "V + object (n.)"
        if idx == 0 or tagged[idx-1][0] == ',': return "Discourse Marker"
        return None

    def _extract_noun_pattern(self, tagged, idx):
        # 针对 terms, way, idea
        if idx + 1 >= len(tagged): return None
        next_w, next_t = tagged[idx+1]
        
        if next_w == 'of': return "N + of + n."  # way of life
        if next_w == 'that': return "N + that-clause" # idea that...
        if next_t == 'TO': return "N + to do" # way to go
        if next_t == 'IN': return f"N + {next_w} + n." # search for...
        return None
        
    def _extract_adj_pattern(self, tagged, idx):
        if idx + 1 >= len(tagged): return None
        next_w, next_t = tagged[idx+1]
        if next_t == 'TO': return "Adj + to do" # happy to see
        if next_t == 'IN': return f"Adj + {next_w} + n." # good at...
        return None

    # ==========================================================
    # 🔵 Engine B: 线性搭配
    # ==========================================================
    def _engine_b_linear(self, target_lemma, genres, grouped_sents):
        collabs_by_genre = {}
        
        for genre in genres:
            sents = grouped_sents[genre]
            if len(sents) < self.MIN_SENTENCE_THRESHOLD: continue
            
            modifiers = Counter()
            objects = Counter()
            examples_map = defaultdict(list)
            
            for text, words_arr in sents:
                try:
                    tagged = nltk.pos_tag(words_arr)
                    indices = [i for i, (w, t) in enumerate(tagged) 
                               if self.normalize_word(w) == target_lemma]
                    
                    for idx in indices:
                        start, end = max(0, idx-3), min(len(tagged), idx+4)
                        for i in range(start, end):
                            if i == idx: continue
                            w, t = tagged[i]
                            if not w.isalpha() or w in self.stopwords: continue
                            
                            phrase = ""
                            item_type = None
                            
                            if i < idx: # 前置修饰
                                if t.startswith('J') or t.startswith('R') or t.startswith('V'):
                                    phrase = f"{w} {target_lemma}"
                                    item_type = 'mod'
                            else: # 后置搭配
                                if t.startswith('N') or t.startswith('I'):
                                    phrase = f"{target_lemma} {w}"
                                    item_type = 'obj'
                            
                            if phrase and item_type:
                                if item_type == 'mod': modifiers[phrase] += 1
                                else: objects[phrase] += 1
                                if len(examples_map[phrase]) < 1:
                                    examples_map[phrase].append(text)
                except: continue
                
            res = {}
            top_mod = [{"p": p, "c": c, "ex": examples_map[p][0]} for p, c in modifiers.most_common(6) if c > 1]
            top_obj = [{"p": p, "c": c, "ex": examples_map[p][0]} for p, c in objects.most_common(6) if c > 1]
            
            if top_mod: res["modifiers"] = top_mod
            if top_obj: res["objects"] = top_obj
            if res: collabs_by_genre[genre] = res
            
        return collabs_by_genre
