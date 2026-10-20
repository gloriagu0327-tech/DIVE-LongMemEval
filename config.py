# ==========================================================
# 配置文件：你只需要改这一个地方
# ==========================================================

# 【第一步】去 https://platform.deepseek.com/ 注册 → 左侧 "API Keys" → 创建一个 key
# 把下面引号里的内容换成你自己的 key（形如 sk-xxxxxxxx）
DEEPSEEK_API_KEY = "sk-b2856a09994c4e0aaef69f17fc59516c"

# DeepSeek 的接口地址（它兼容 OpenAI 的格式，不用改）
BASE_URL = "https://api.deepseek.com"

# 用哪个模型答题。deepseek-chat 便宜又够聪明，先用它。
MODEL = "deepseek-chat"

# 数据文件路径（已经帮你放好了，不用改）
DATA_PATH = "data/longmemeval_oracle.json"

# 先拿多少道题试跑
NUM_QUESTIONS = 500

# 是否把历史对话先"提炼成干净事实"再存记忆（V2 升级，强烈建议开着）
# True = 用模型把每段对话压缩成事实清单，喂给回答模型的更干净，答对率更高
# False = 退回 V1 的原样存对话（更省调用，但更容易被闲聊噪音干扰）
EXTRACT_FACTS = True

# 每次答题时，从记忆里捞出最相关的几条给大模型
# 事实版记忆更干净，10 条足够；如果答案经常找不到，可以调大到 15
TOP_K = 10

# 是否开启"跨会话均衡检索"（V4 升级，针对 multi-session 题）
# True = 每个会话各取几条，保证多会话都被覆盖（multi-session 题提升大）
# False = 退回 V3 的全局取 topK（可能全挤在一个会话里）
BALANCE_SESSIONS = False

# 是否使用语义检索（V5 实验：500题测出来 56%，和关键词持平，没带来提升，已弃用）
# 现在保持 False，退回关键词检索，配合 TOP_K=18 看效果
USE_SEMANTIC = False