# ==========================================================
# 主程序：跑前 N 道题，输出 predictions.jsonl
# 运行方法：python run_demo.py
#
# 【V3 升级】
# 1. 按题型分别统计正确率 —— 一眼看清哪类题最弱
# 2. 断点续跑 —— 每答完一题就存一次，中断了重跑会跳过已答的题
# 3. 精简输出 —— 只显示每题结果，减少刷屏
# ==========================================================

import json
import os
import sys
import config

# 防止 Windows 控制台打印中文时报 ascii 编码错误
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# 启动前检查：API key 是否填了（防止用中文占位符当 key 导致调用失败）
PLACEHOLDER = "在这里粘贴你的key"
if not config.DEEPSEEK_API_KEY or config.DEEPSEEK_API_KEY.strip() in (PLACEHOLDER, ""):
    print("【错误】config.py 里的 DEEPSEEK_API_KEY 还没填！")
    print("请打开 config.py，把 '在这里粘贴你的key' 替换成你注册 DeepSeek 后拿到的真实 key（sk- 开头）。")
    sys.exit(1)

from memory_system import ingest_sessions, retrieve, answer_question

OUT_PATH = "predictions.jsonl"


def _rough_correct(gold, hypo):
    """粗略判断答对没：答案关键词是否出现在回答里，且没说'不知道'。
    仅供自己看趋势，正式评分以官方 evaluate_qa.py 为准。"""
    if "don't know" in hypo.lower():
        return False
    gold = str(gold)  # 标准答案可能是数字，先转成字符串
    gold_words = set(gold.lower().split())
    return len(gold_words & set(hypo.lower().split())) >= 1


def main():
    with open(config.DATA_PATH, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    subset = dataset[: config.NUM_QUESTIONS]
    print(f"本次共 {len(subset)} 道题\n")

    # 断点续跑：先读已存在的预测结果
    done = {}
    if os.path.exists(OUT_PATH):
        with open(OUT_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    obj = json.loads(line)
                    done[obj["question_id"]] = obj["hypothesis"]
        if done:
            print(f"检测到已有 {len(done)} 题结果，将跳过它们继续跑（断点续跑）\n")

    results = {qid: h for qid, h in done.items()}

    for i, item in enumerate(subset):
        qid = item["question_id"]
        if qid in results:  # 已答过，跳过
            continue

        q = item["question"]
        qdate = item["question_date"]
        gold = item["answer"]
        qtype = item["question_type"]

        try:
            memories = ingest_sessions(item)
            top_memories = retrieve(q, memories)
            hypo = answer_question(q, qdate, top_memories)
        except Exception as e:
            hypo = f"[调用失败] {e}"

        results[qid] = hypo

        # 答完立即存盘，实现断点续跑
        with open(OUT_PATH, "w", encoding="utf-8") as f:
            for qid2, h2 in results.items():
                f.write(json.dumps({"question_id": qid2, "hypothesis": h2}, ensure_ascii=False) + "\n")

        ok = "✔" if _rough_correct(gold, hypo) else "✘"
        print(f"[{i+1}/{len(subset)}] {ok} {qtype}")
        print(f"   {q[:80]}")
        print(f"   标准: {gold}")
        print(f"   我的: {hypo[:100]}")
        print("-" * 50)

    # ===== 按题型统计 =====
    print("\n" + "=" * 60)
    print("【按题型统计正确率】")
    from collections import defaultdict
    stats = defaultdict(lambda: [0, 0])  # 题型 -> [答对, 总数]
    for item in subset:
        qid = item["question_id"]
        qtype = item["question_type"]
        gold = item["answer"]
        hypo = results.get(qid, "")
        stats[qtype][1] += 1
        if _rough_correct(gold, hypo):
            stats[qtype][0] += 1

    total_ok = sum(v[0] for v in stats.values())
    total = sum(v[1] for v in stats.values())
    for qtype, (ok, n) in sorted(stats.items(), key=lambda x: -x[1][0] / max(x[1][1], 1)):
        print(f"  {qtype:<28} {ok:>3}/{n:<3}  {ok/n*100:.0f}%")
    print("-" * 60)
    print(f"  总计              {total_ok:>3}/{total:<3}  {total_ok/total*100:.0f}%")
    print(f"\n结果已写入 {OUT_PATH}")


if __name__ == "__main__":
    main()
