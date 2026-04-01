import json
import os
import re
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

# --- 1. 配置区域 ---
load_dotenv()

MODEL_NAME = os.getenv("MODEL_NAME", "qwen2.5:7b")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

# 建议：由于实体类型变多，Prompt 变长，建议稍微减小分块大小以保证提取质量
CHUNK_SIZE = int(os.getenv("EXTRACTION_CHUNK_SIZE", 1200))
OVERLAP = 200
MAX_RETRIES = 2

# --- 2. 路径配置 ---
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
INPUT_FILE = DATA_DIR / os.getenv("RAW_TXT_FILE", "三国演义.txt")
OUTPUT_FILE = DATA_DIR / "rich_extracted_advanced.json"
TEMP_FILE = DATA_DIR / "rich_extracted_temp.json"
INDEX_FILE = DATA_DIR / ".progress_index"

# --- 3. 深度优化的本体定义 ---

# 👇 扩展后的实体类型
ENTITY_TYPES = [
    "人物",  # 核心角色
    "势力",  # 政治集团
    "地点",  # 州郡、关隘、城池
    "官职",  # 职位
    "家族",  # 姓氏宗族（如：夏侯氏、司马氏）
    "武器",  # 兵器、铠甲
    "坐骑",  # 马匹
    "宝物",  # 书籍、玉玺、珍宝
    "战役",  # 战争事件
    "事件",  # 一般性历史事件（如：桃园结义、三顾茅庐）
    "朝代",  # 历史时期
    "文学意象",  # 字号、绰号（如：卧龙、凤雏、美髯公）
    "典籍"  # 兵书、经书
]

# 👇 优化后的关系类型（分类明确，语义丰富）
RELATION_TYPES = [
    # --- 社会关系 ---
    "隶属",  # 人物 -> 势力 (替代"隶属于")
    "担任",  # 人物 -> 官职
    "亲属",  # 人物 -> 人物 (父子、兄弟等)
    "配偶",  # 人物 -> 人物 (夫妻)
    "结义",  # 人物 -> 人物 (桃园结义)
    "师从",  # 人物 -> 人物 (师徒)
    "举荐",  # 人物 -> 人物 (推荐人才)
    "同僚",  # 人物 -> 人物 (同事)

    # --- 交互/冲突 ---
    "敌对",  # 人物/势力 -> 人物/势力
    "交战",  # 势力 -> 势力
    "斩杀",  # 人物 -> 人物 (战斗结果)
    "擒获",  # 人物 -> 人物
    "投降",  # 人物 -> 人物/势力
    "辅佐",  # 人物 -> 人物 (谋士对主公)

    # --- 拥有/使用 ---
    "拥有",  # 人物 -> 武器/宝物/坐骑
    "使用",  # 人物 -> 武器/计谋

    # --- 地理/位置 ---
    "定都",  # 势力 -> 地点
    "镇守",  # 人物 -> 地点
    "位于",  # 地点 -> 地点
    "出生地",  # 人物 -> 地点

    # --- 参与/发生 ---
    "参与",  # 人物 -> 战役/事件
    "指挥",  # 人物 -> 战役
    "发生地",  # 战役/事件 -> 地点
    "实施",  # 人物 -> 计谋/事件
]


def split_text(text, size, overlap):
    """智能分块"""
    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = start + size
        if end >= text_len:
            chunks.append(text[start:])
            break

        # 寻找标点
        last_punct = max(text.rfind('。', start, end), text.rfind('！', start, end), text.rfind('？', start, end))
        if last_punct > start + size * 0.5:
            end = last_punct + 1

        chunks.append(text[start:end])
        start = end - overlap
        if start <= len(chunks) * (size - overlap) - (size - overlap):
            start += size - overlap
    return chunks


def extract_json_from_response(text):
    """JSON 提取与清洗"""
    if not text.strip(): return None
    text = re.sub(r'```json\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'```\s*', '', text)

    start_idx = text.find('{')
    end_idx = text.rfind('}')

    if start_idx != -1 and end_idx != -1:
        json_str = text[start_idx: end_idx + 1]
        try:
            return json.loads(json_str)
        except:
            # 简单修复
            fixed = re.sub(r',\s*}', '}', json_str)
            fixed = re.sub(r',\s*]', ']', fixed)
            try:
                return json.loads(fixed)
            except:
                return None
    return None


def extract_chunk(chunk, client, retry_count=0):
    # 构建类型字符串
    entity_types_str = ", ".join([f'"{t}"' for t in ENTITY_TYPES])
    relation_types_str = ", ".join([f'"{t}"' for t in RELATION_TYPES])

    # 👇 强化的 Prompt：包含定义和示例
    prompt = f"""system
You are an expert Knowledge Graph extractor for "Romance of the Three Kingdoms".
DO NOT think step-by-step. Output ONLY raw JSON.

### Entity Types ###
{entity_types_str}

### Relation Types ###
{relation_types_str}

### Instructions ###
1. Extract entities and relations from the text.
2. STRICTLY use the types listed above.
3. For "人物" entities, if a nickname (e.g., "卧龙") is mentioned, extract it as a separate entity of type "文学意象" and link it.
4. Be precise with relations: use "斩杀" instead of generic "敌对" if someone is killed. Use "举荐" if someone recommends another.

### Example Output ###
{{
  "entities": [
    {{"name": "关羽", "type": "人物"}},
    {{"name": "赤兔马", "type": "坐骑"}},
    {{"name": "美髯公", "type": "文学意象"}}
  ],
  "relations": [
    {{"source": "关羽", "target": "赤兔马", "type": "拥有"}},
    {{"source": "关羽", "target": "美髯公", "type": "被称为"}}
  ]
}}

Text:
{chunk}
"""

    try:
        response = client.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.01, "num_predict": 2048, "num_ctx": 8192}
            },
            timeout=120.0
        )
        content = response.json().get("response", "")

        if not content.strip():
            if retry_count < MAX_RETRIES:
                time.sleep(2)
                return extract_chunk(chunk, client, retry_count + 1)
            return {"entities": [], "relations": []}

        result = extract_json_from_response(content)

        if result is None:
            if retry_count < MAX_RETRIES:
                time.sleep(2)
                return extract_chunk(chunk, client, retry_count + 1)
            return {"entities": [], "relations": []}

        return result

    except Exception as e:
        if retry_count < MAX_RETRIES:
            time.sleep(2)
            return extract_chunk(chunk, client, retry_count + 1)
        return {"entities": [], "relations": []}


def load_checkpoint():
    if INDEX_FILE.exists() and TEMP_FILE.exists():
        try:
            with open(INDEX_FILE, "r") as f:
                start_idx = int(f.read().strip())
            with open(TEMP_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            print(f"⏩ 恢复进度：从第 {start_idx} 片开始")
            return start_idx, data
        except:
            pass
    return 0, {"entities": [], "relations": []}


def main():
    if not INPUT_FILE.exists():
        print(f"❌ 找不到文件：{INPUT_FILE}")
        return

    print(f"🔍 检查 Ollama...")
    try:
        with httpx.Client() as check_client:
            check_client.get(f"{OLLAMA_HOST}/api/tags", timeout=5.0)
    except Exception as e:
        print(f"❌ 连接失败：{e}")
        return

    print(f"📖 读取文本...")
    try:
        text = INPUT_FILE.read_text(encoding="utf-8")
    except:
        text = INPUT_FILE.read_text(encoding="gb18030")

    chunks = split_text(text, CHUNK_SIZE, OVERLAP)
    print(f"📊 分块：{len(chunks)} 片")

    start_idx, all_data = load_checkpoint()
    all_entities = all_data.get("entities", [])
    all_relations = all_data.get("relations", [])

    print(f"🚀 开始深度提取...")
    with httpx.Client() as client:
        for i in range(start_idx, len(chunks)):
            chunk = chunks[i]
            print(f"\r[{i + 1}/{len(chunks)}] 处理中...", end="", flush=True)

            result = extract_chunk(chunk, client)

            if result.get("entities"): all_entities.extend(result["entities"])
            if result.get("relations"): all_relations.extend(result["relations"])

            # 保存进度
            with open(INDEX_FILE, "w") as f:
                f.write(str(i + 1))
            with open(TEMP_FILE, "w", encoding="utf-8") as f:
                json.dump({"entities": all_entities, "relations": all_relations}, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 30)
    print("✅ 提取完成！")
    print(f"   实体：{len(all_entities)}")
    print(f"   关系：{len(all_relations)}")

    OUTPUT_FILE.write_text(
        json.dumps({"entities": all_entities, "relations": all_relations}, ensure_ascii=False, indent=2),
        encoding="utf-8")

    if TEMP_FILE.exists(): TEMP_FILE.unlink()
    if INDEX_FILE.exists(): INDEX_FILE.unlink()


if __name__ == "__main__":
    main()