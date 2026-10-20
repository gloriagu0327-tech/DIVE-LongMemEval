import json

# 1. 读取你的文件（注意：如果此时你的py文件在data文件夹里，这里写 'longmemeval_oracle.json'；如果在外面，写 'data/longmemeval_oracle.json'）
file_path = 'longmemeval_oracle.json' 

try:
    with open(file_path, 'r', encoding='utf-8') as f:
        dataset = json.load(f)
        
    print(f"数据集总共有 {len(dataset)} 道题。\n")
    
    for i in range(3):
        item = dataset[i]
        print("="*50)
        print(f"【第 {i+1} 题】")
        print(f"题型: {item.get('question_type')}")
        print(f"问题: {item.get('question')}")
        print(f"答案: {item.get('answer')}")
        sessions = item.get('haystack_sessions', [])
        print(f"历史对话片段数量: {len(sessions)} 段")
        print("="*50 + "\n")
        
except FileNotFoundError:
    print("找不到文件！请检查文件名和路径是否正确。")
except Exception as e:
    print(f"出错了: {e}")

    # 统计所有题型
type_count = {}
for item in dataset:
    q_type = item.get('question_type', '未知')
    type_count[q_type] = type_count.get(q_type, 0) + 1

print("【全局题型分布】")
for k, v in type_count.items():
    print(f"{k}: {v} 题")