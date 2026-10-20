# ==========================================================
# 配置文件：你只需要改这一个地方
# ==========================================================

# 【第一步】去 https://platform.deepseek.com/ 注册 → 左侧 "API Keys" → 创建一个 key
# 把下面引号里的内容换成你自己的 key（形如 sk-xxxxxxxx）
DEEPSEEK_API_KEY = "sk-bac95209d66249bda5d40ee915b3fd8f"

# DeepSeek 的接口地址（它兼容 OpenAI 的格式，不用改）
BASE_URL = "https://api.deepseek.com"

# 用哪个模型答题。deepseek-chat 便宜又够聪明，先用它。
MODEL = "deepseek-chat"

# 数据文件路径（已经帮你放好了，不用改）
DATA_PATH = "data/longmemeval_oracle.json"

# 先拿多少道题试跑（先用 10 题跑通，别一上来跑 500）
NUM_QUESTIONS = 10

# 是否把历史对话先"提炼成干净事实"再存记忆（V2 升级，强烈建议开着）
# True = 用模型把每段对话压缩成事实清单，喂给回答模型的更干净，答对率更高
# False = 退回 V1 的原样存对话（更省调用，但更容易被闲聊噪音干扰）
EXTRACT_FACTS = True

# 每次答题时，从记忆里捞出最相关的几条给大模型
# 事实版记忆更干净，10 条足够；如果答案经常找不到，可以调大到 15
TOP_K = 10
