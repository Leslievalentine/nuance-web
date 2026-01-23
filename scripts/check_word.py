import psycopg2
import sys
from scripts.synonym_service import SynonymEngine

DB_CONFIG = {
    "dbname": "nuance_engine_db", "user": "postgres", "password": "5432", 
    "host": "localhost", "options": "-c client_encoding=utf8"
}

def print_ascii_bar(percent, length=15):
    filled = int(length * percent / 100)
    return '█' * filled + '░' * (length - filled)

def display_word_report(word):
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    # 1. 基础信息
    cur.execute("SELECT id, processing_strategy, definition_cn, bnc_rank FROM words WHERE spelling = %s", (word,))
    row = cur.fetchone()
    
    if not row:
        print(f"❌ 未收录单词: {word}")
        return
        
    wid, strategy, def_cn, rank = row
    
    # 2. 分析结果
    cur.execute("SELECT register_stats, analysis_data FROM word_nuance_profiles WHERE word_id = %s", (wid,))
    res_row = cur.fetchone()
    
    print("\n" + "═"*70)
    print(f"📘 {word.upper()}  |  Rank: #{rank}  |  Type: {strategy}")
    print(f"📝 {def_cn}")
    print("═"*70)

    # 3. 🔗 智能近义词推荐 (置顶显示)
    eng = SynonymEngine()
    syns = eng.get_synonyms_scored(word)
    
    if syns:
        print(f"\n🔗 [近义词辨析群] (Synonym Cluster)")
        # Top 3 推荐
        print(f"   ⭐ 核心推荐:")
        for i, s in enumerate(syns[:3]):
            print(f"      {i+1}. {s['spelling'].ljust(12)} (Sim: {s['score']:.2f}) - {s['def'][:30]}...")
            
        # 更多
        if len(syns) > 3:
            others = [s['spelling'] for s in syns[3:]]
            print(f"   📂 其他族群: {', '.join(others[:8])}...")
        
        target = syns[0]['spelling']
        print(f"   💡 对比指令: python -m scripts.check_word duel {word} {target}")
    else:
        print(f"\n🔗 [近义词辨析群]: (暂无高相似度且已收录的近义词)")

    if not res_row:
        print("\n⚠️ 暂无深度分析数据")
        return
        
    reg_stats, analysis = res_row
    
    # 4. 📊 双源语域雷达 (恢复 ASCII 条)
    print(f"\n📊 [语域分布概览] (Register Distribution)")
    for source in ['BNC', 'MASC']:
        stats = reg_stats.get(source, {})
        if not stats: continue
        total = sum(stats.values())
        if total == 0: continue
        
        print(f"   🏛️  {source} 来源:")
        # 排序前 4 个
        sorted_stats = sorted(stats.items(), key=lambda x: x[1], reverse=True)[:4]
        for g, c in sorted_stats:
            pct = (c/total)*100
            bar = print_ascii_bar(pct)
            print(f"      {g.ljust(18)} : {bar} {pct:.1f}% ({c})")

    # 5. 🧠 核心构式/搭配 (恢复完整列表)
    print(f"\n🧠 [核心用法提取] ({strategy} Mode)")
    
    if not analysis:
        print("   (数据量不足以进行深度挖掘)")
    else:
        for genre, items in analysis.items():
            print(f"\n   🌍 语境: {genre}")
            
            if strategy == 'PATTERN':
                # Pattern 模式: 显示模板 + 例句
                for p in items[:3]: # 每个语域只显示前3个句式，避免刷屏
                    print(f"      🔹 {p['template'].ljust(25)} ({p['count']})")
                    if p['examples']: 
                        print(f"         └─ \"{p['examples'][0][:80]}...\"")
                    
            elif strategy == 'LINEAR':
                # Linear 模式: 分开显示修饰和搭配
                if 'modifiers' in items:
                    print("      👉 前置修饰 (Modifiers):")
                    for m in items['modifiers'][:4]: # 显示前4个
                        print(f"         • {m['p']} ({m['c']})")
                
                if 'objects' in items:
                    print("      👉 后置搭配 (Objects/Verbs):")
                    for o in items['objects'][:4]: # 显示前4个
                        print(f"         • {o['p']} ({o['c']})")

    print("\n" + "─"*70 + "\n")

def display_duel_report(word_a, word_b):
    # 复用之前已提供的 Duel 代码，请确保这部分逻辑存在
    engine = SynonymEngine()
    print(f"\n⚖️  正在进行深度对比分析: {word_a} vs {word_b} ...")
    report = engine.duel_words(word_a, word_b)
    if not report:
        print("❌ 对比失败。")
        return
    print("\n" + "═"*70)
    print(f"🥊 近义词深度辨析: {word_a.upper()} vs {word_b.upper()}")
    print("═"*70)
    print("\n📡 [语域使用倾向] (Register Preference)")
    for source, diffs in report['register_contrast'].items():
        print(f"\n   🏛️  {source} 语料库数据:")
        print(f"      {'领域 (Genre)':<20} | {word_a:<10} vs {word_b:<10} | 优势词")
        print("      " + "─"*65)
        for d in diffs:
            winner = word_a if d['delta'] > 5 else (word_b if d['delta'] < -5 else "=")
            marker = "◄" if winner == word_a else ("►" if winner == word_b else "")
            print(f"      {d['genre']:<20} | {d['a_pct']:4.1f}%      {d['b_pct']:4.1f}%      | {winner} {marker}")
    print("\n\n🧩 [特有搭配] (Distinctive Collocations)")
    col = report['collocation_contrast']
    print(f"   👉 {word_a} 特有: " + ", ".join(col['unique_a']))
    print(f"   👉 {word_b} 特有: " + ", ".join(col['unique_b']))
    print("\n" + "═"*70 + "\n")

def main():
    if len(sys.argv) < 2: return
    cmd = sys.argv[1]
    if cmd == 'duel' and len(sys.argv) >= 4:
        display_duel_report(sys.argv[2], sys.argv[3])
    else:
        display_word_report(cmd)

if __name__ == "__main__":
    main()
