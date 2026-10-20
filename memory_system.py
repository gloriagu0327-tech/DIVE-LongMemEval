# ==========================================================
# 记忆系统核心（V2·事实提炼版）：ingest → retrieve → generate
# 升级点：不再"无差别存储原始对话"，而是先让模型把每段对话
#         提炼成【干净的事实清单】（带日期），再存进记忆。
#         —— 正好对应手册 Accumulate 能力的要求。
# ==========================================================

import re
from openai import OpenAI
import config


# ----------------------------------------------------------
# 1) INGEST：把历史对话"提炼"成事实，存成记忆
#    每条记忆 = { text: 一条事实, role, date }
# ----------------------------------------------------------

def _extract_facts_from_session(session_turns, date):
    """
    把一段对话（多条 user/assistant 轮次）交给模型，提炼成几条干净的事实。
    返回字符串列表，例如 ["user attended Holi on Feb 26, 2023", "..."]
    如果提炼失败，退回去原样存对话轮次（保证不崩）。
    """
    # 把这段对话整理成模型能读的文本
    dialogue = ""
    for t in session_turns:
        role = t.get("role", "unknown")
        content = t.get("content", "").strip()
        if content:
            dialogue += f"{role}: {content}\n"

    prompt = f"""You are building a long-term memory for the user from their conversation.
Read the conversation below and extract every DURABLE FACT about the user's life —
things like: events they attended (with dates), purchases, preferences, family,
schedule, plans, possessions, and any change or update to a previously known fact.
IGNORE: generic assistant advice, small talk with no real facts, repeated pleasantries.

Rules:
- Output each fact on its own line, starting with "FACT: ".
- Keep each fact short and concrete. If a date is mentioned, include it (e.g. "on Feb 26, 2023").
- If the same fact is stated then later UPDATED, output the LATEST version only.
- Output ONLY the FACT lines, nothing else.

Conversation:
{dialogue}"""

    client = get_client()
    resp = client.chat.completions.create(
        model=config.MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
    )
    raw = resp.choices[0].message.content.strip()
    facts = [line.strip()[6:].strip() for line in raw.splitlines()
             if line.strip().startswith("FACT:")]
    return facts


def ingest_sessions(question_item):
    """
    输入：json 里的一道题（含历史对话 haystack_sessions）
    输出：记忆列表，每条记忆 = { text: 事实, role: "user", date }
    """
    memories = []
    sessions = question_item["haystack_sessions"]
    dates = question_item.get("haystack_dates", [])

    for i, session in enumerate(sessions):
        date = dates[i] if i < len(dates) else "未知日期"
        try:
            facts = _extract_facts_from_session(session, date)
        except Exception:
            facts = []
        if facts:
            # 提炼成功：把每条事实当作一条记忆，并记录来自哪个会话（session_idx）
            for f in facts:
                memories.append({"text": f, "role": "user", "date": date, "session_idx": i})
        else:
            # 提炼失败：退回去原样存对话轮次，保证不崩
            for turn in session:
                content = turn.get("content", "").strip()
                if content:
                    memories.append({
                        "text": content,
                        "role": turn.get("role", "unknown"),
                        "date": date,
                        "session_idx": i,
                    })
    return memories


# ----------------------------------------------------------
# 2) RETRIEVE：拿问题去记忆里搜，捞出最相关的几条
#    现在记忆是干净事实，检索会更准。仍用简单关键词重合度打分。
# ----------------------------------------------------------
STOPWORDS = set(
    "what was the a an of in on at to i my me is are were did do does which who when where "
    "how and or but for with about you your he she it they this that these those from "
    "have has had will would can could should not no yes there here been being just".split()
)


def _keywords(text):
    words = re.findall(r"[a-zA-Z]+", text.lower())
    return [w for w in words if w not in STOPWORDS and len(w) > 2]


# ==========================================================
# 语义检索（V5）：用 embedding 向量找"意思相近"的记忆
# 比关键词检索准得多，对 preference / assistant / multi-session 提升明显
# ==========================================================
_embedder = None   # 懒加载：第一次用到才加载模型


def _get_embedder():
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer
        # 多语言小模型，能处理中英文混合（数据是英文，用这模型也够）
        _embedder = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    return _embedder


def _semantic_retrieve(question, memories, top_k):
    """语义检索：给每条记忆和问题算向量，按余弦相似度排序取前 top_k。"""
    try:
        model = _get_embedder()
        texts = [m["text"] for m in memories]
        q_vec = model.encode([question])
        m_vecs = model.encode(texts)
        # 余弦相似度
        import numpy as np
        q_norm = q_vec / np.linalg.norm(q_vec)
        m_norm = m_vecs / np.linalg.norm(m_vecs, axis=1, keepdims=True)
        sims = (m_norm @ q_norm.T).flatten()
        # 按相似度排序
        order = sims.argsort()[::-1]
        picked = [memories[i] for i in order[:top_k]]
        return picked
    except Exception as e:
        # 语义检索失败就退回关键词
        print(f"[警告] 语义检索失败({e})，退回关键词检索")
        return _keyword_retrieve(question, memories, top_k)


def _keyword_retrieve(question, memories, top_k):
    """关键词检索：原逻辑（按关键词重合度）。"""
    q_words = set(_keywords(question))
    scored = []
    for m in memories:
        m_words = set(_keywords(m["text"]))
        score = len(q_words & m_words)
        scored.append((score, m))
    scored = [x for x in scored if x[0] > 0]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [m for score, m in scored[:top_k]]


def retrieve(question, memories, top_k=config.TOP_K):
    """检索总入口：优先语义检索（如开启），否则关键词检索。"""
    # 语义检索开关
    if getattr(config, "USE_SEMANTIC", False):
        return _semantic_retrieve(question, memories, top_k)
    return _keyword_retrieve(question, memories, top_k)


# ----------------------------------------------------------
# 3) GENERATE：把捞出的记忆 + 问题 交给大模型回答
# ----------------------------------------------------------
_client = None


def get_client():
    global _client
    if _client is None:
        _client = OpenAI(api_key=config.DEEPSEEK_API_KEY, base_url=config.BASE_URL)
    return _client


def answer_question(question, question_date, memories):
    memory_text = ""
    for m in memories:
        memory_text += f"- [{m['date']}] {m['text']}\n"

    prompt = f"""You are answering a question about the user's PAST conversations.
You may ONLY use the memory records below. Do NOT use outside knowledge.
If the answer is truly not in the memories, reply exactly: I don't know.

Facts about the user (each line starts with [the date the fact was known]):
{memory_text}

Today is {question_date}.

Important instructions:
- If the question asks "how many days / how long / which came first / before or after", find the DATES in the facts, then do the date arithmetic yourself.
- If a fact appears with different values across dates, use the LATEST one.
- Give a SHORT, direct answer (a few words or a short phrase).
Question: {question}
Answer:"""

    client = get_client()
    resp = client.chat.completions.create(
        model=config.MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
    )
    return resp.choices[0].message.content.strip()
