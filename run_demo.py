# ==========================================================
# 主程序：跑前 N 道题，输出 predictions.jsonl
# 运行方法：在终端里进入本文件夹，输入  python run_demo.py
# ==========================================================

import json
import config
from memory_system import ingest_sessions, retrieve, answer_question


def main():
    # 1. 读数据
    with open(config.DATA_PATH, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    subset = dataset[: config.NUM_QUESTIONS]
    print(f"本次试跑 {len(subset)} 道题...\n")

    results = []
    rough_correct = 0

    for i, item in enumerate(subset):
        qid = item["question_id"]
        q = item["question"]
        qdate = item["question_date"]
        gold = item["answer"]  # 标准答案，只用于你自己粗看对错，正式系统里不能用

        # 2. ingest：吃进历史
        memories = ingest_sessions(item)

        # 3. retrieve：捞出相关记忆
        top_memories = retrieve(q, memories)

        # 4. generate：让大模型根据记忆回答
        try:
            hypo = answer_question(q, qdate, top_memories)
        except Exception as e:
            hypo = f"[调用失败] {e}"

        # 5. 存下来（这就是最后要交的 JSONL 格式）
        results.append({"question_id": qid, "hypothesis": hypo})

        # 粗评：答案关键词有没有出现在我们的回答里（仅供你自己看趋势，不是官方评分）
        gold_words = set(gold.lower().split())
        hit = len(gold_words & set(hypo.lower().split())) >= 1 and "don't know" not in hypo.lower()
        if hit:
            rough_correct += 1

        print(f"[{i+1}/{len(subset)}] 题型:{item['question_type']}")
        print(f"   问题: {q}")
        print(f"   标准: {gold}")
        print(f"   我的: {hypo}")
        print(f"   捞出 {len(top_memories)}/{len(memories)} 条记忆")
        print("-" * 60)

    # 6. 写出 JSONL 文件（每行一个 {question_id, hypothesis}）
    with open("predictions.jsonl", "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"\n完成！结果已写入 predictions.jsonl")
    print(f"粗看正确率（仅供参考，不是官方分）: {rough_correct}/{len(subset)}")


if __name__ == "__main__":
    main()
#（注：内容由AI生成）
