import os
import json
import re
import requests
import time
from tqdm import tqdm
from pathlib import Path

# ================= 配置 =================
# 获取当前脚本所在的目录
SCRIPT_DIR = Path(__file__).parent
# 项目根目录 (脚本的父目录)
ROOT_DIR = SCRIPT_DIR.parent

# 定义文件路径 (使用绝对路径，避免运行目录问题)
INPUT_FILE = ROOT_DIR / "data" / "三国演义.txt"
EXISTING_KG_FILE = ROOT_DIR / "data" / "sanguo_kg_final.json"
OUTPUT_FILE = ROOT_DIR / "data" / "sanguo_kg_complete.json"

MODEL_NAME = "qwen2.5:7b"  # 关键：必须用不带思考的模型
OLLAMA_HOST = "http://localhost:11434"
CHUNK_SIZE = 1000  # 减小分块，提高关系提取准确率
OVERLAP = 150


# =======================================

def split_text(text):
    """智能分块，尽量在句子结束处切断"""
    chunks = []
    start = 0
    text_len = len(text)
    while start < text_len:
        end = start + CHUNK_SIZE
        if end < text_len:
            # 寻找最近的句号、感叹号或问号
            last_punct = -1
            for p in ['。', '！', '？', '\n']:
                pos = text.rfind(p, start, end)
                if pos > last_punct:
                    last_punct = pos

            if last_punct > start + CHUNK_SIZE * 0.5:
                end = last_punct + 1

        chunks.append(text[start:end])
        start = end - OVERLAP
        if start >= text_len:
            break
        if start <= 0:  # 防止死循环
            start += CHUNK_SIZE
    return chunks


def extract_relations_from_chunk(chunk):
    """
    专门提取关系的 Prompt，忽略实体，只关注关系三元组
    """
    prompt = f"""<|im_start|>system
You are a data extractor. Output ONLY a raw JSON list of relations.
Format: [{{"source": "Name", "target": "Name", "type": "Type"}}]
No markdown, no thinking, no explanations.
If no relations found, output [].
<|im_end|>
<|im_start|>user
Text: {chunk}
Extract relations between people, places, and organizations.
<|im_end|>
<|im_start|>assistant
["""

    try:
        resp = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.01, "num_predict": 1500}
            },
            timeout=60
        )

        raw_text = resp.json().get("response", "")

        # --- 强力清洗逻辑 ---
        raw_text = raw_text.replace("```json", "").replace("```", "").strip()

        if not raw_text.startswith('['):
            start_idx = raw_text.find('[')
            if start_idx != -1:
                raw_text = raw_text[start_idx:]
            else:
                raw_text = "["

        if not raw_text.endswith(']'):
            end_idx = raw_text.rfind(']')
            if end_idx != -1:
                raw_text = raw_text[:end_idx + 1]
            else:
                raw_text = raw_text + "]"

        raw_text = re.sub(r',\s*]', ']', raw_text)
        raw_text = re.sub(r',\s*}', '}', raw_text)

        data = json.loads(raw_text)

        if isinstance(data, list):
            return data
        else:
            if isinstance(data, dict) and 'relations' in data:
                return data['relations']
            return []

    except Exception as e:
        # 静默失败，继续处理下一个
        return []


def main():
    print(f"📂 工作目录: {ROOT_DIR}")
    print(f"📖 加载现有知识图谱: {EXISTING_KG_FILE}")

    existing_entities = []

    if EXISTING_KG_FILE.exists():
        with open(EXISTING_KG_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            existing_entities = data.get('entities', [])
            print(f"✅ 已加载 {len(existing_entities)} 个实体。")
    else:
        print("⚠️ 未找到现有文件 ({EXISTING_KG_FILE})，将从头开始（仅提取关系，实体列表将为空）。")

    if not INPUT_FILE.exists():
        print(f"❌ 输入文件不存在: {INPUT_FILE}")
        print("💡 请确认 data/三国演义.txt 是否存在。")
        return

    print("✂️ 正在分块...")
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        text = f.read()

    chunks = split_text(text)
    print(f"📊 共分为 {len(chunks)} 个块。")

    all_relations = []

    print("🚀 开始提取关系 (这可能需要几分钟)...")
    for i, chunk in enumerate(tqdm(chunks)):
        rels = extract_relations_from_chunk(chunk)
        if rels:
            all_relations.extend(rels)
        if i % 10 == 0:
            time.sleep(0.1)

    print("\n🧹 正在清洗和去重关系...")
    unique_relations = []
    seen_signatures = set()

    # 如果已有实体，建立集合用于参考（可选）
    entity_names = {e['name'] for e in existing_entities}

    valid_count = 0
    duplicate_count = 0

    for r in all_relations:
        src = r.get('source', '').strip()
        tgt = r.get('target', '').strip()
        typ = r.get('type', 'Related').strip()

        if not src or not tgt:
            continue

        sig = f"{src}||{tgt}||{typ}"
        if sig not in seen_signatures:
            seen_signatures.add(sig)
            unique_relations.append({
                "source": src,
                "target": tgt,
                "type": typ
            })
            valid_count += 1
        else:
            duplicate_count += 1

    final_data = {
        "entities": existing_entities,
        "relations": unique_relations
    }

    print(f"💾 保存结果到: {OUTPUT_FILE}")
    print(f"   - 实体总数: {len(existing_entities)}")
    print(f"   - 新增有效关系数: {len(unique_relations)}")
    print(f"   - 过滤掉的重复项: {duplicate_count}")

    # 确保 data 目录存在
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)

    print("\n✅ 修复完成！")
    print("👉 下一步操作:")
    print(f"   1. 备份旧文件 (可选): mv {EXISTING_KG_FILE} {EXISTING_KG_FILE}.bak")
    print(f"   2. 覆盖旧文件: cp {OUTPUT_FILE} {EXISTING_KG_FILE}")
    print(f"   3. 重新运行导入: python scripts/import_rich_to_neo4j.py")


if __name__ == "__main__":
    main()