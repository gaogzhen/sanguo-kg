import os
import json
import httpx
from tqdm import tqdm
from dotenv import load_dotenv
from pathlib import Path

# 加载环境变量
load_dotenv()

# --- 🚀 核心修改：自动获取脚本所在目录的父目录 ---
BASE_DIR = Path(__file__).resolve().parent.parent

# 现在基于 BASE_DIR 构建路径，无论在哪里运行都不会错
DATA_DIR = BASE_DIR / "data"
INPUT_FILE = DATA_DIR / os.getenv("RAW_TXT_FILE", "三国演义.txt")
OUTPUT_FILE = DATA_DIR / "rich_extracted.json" # 输出也放到 data 目录

# 其他配置保持不变
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
MODEL_NAME = os.getenv("MODEL_NAME", "qwen3.5")
CHUNK_SIZE = int(os.getenv("EXTRACTION_CHUNK_SIZE", 1500))

# 定义我们要提取的实体类型
ENTITY_TYPES = ["Person", "Location", "Battle", "Time", "Weapon", "Title", "Event"]


def split_text(text, size):
    # 尝试按句子分割，避免切断语义，这里简化为按字符
    return [text[i:i + size] for i in range(0, len(text), size)]


def extract_chunk(chunk, client):
    prompt = f"""
    你是一个三国知识图谱专家。请从以下文本片段中提取实体和关系。

    需要提取的实体类型：{', '.join(ENTITY_TYPES)}
    - Person: 人物 (如：刘备, 关羽)
    - Location: 地点 (如：荆州, 洛阳, 赤壁)
    - Battle: 战役 (如：赤壁之战, 官渡之战)
    - Time: 时间 (如：建安十三年, 初平元年)
    - Weapon: 武器/坐骑 (如：青龙偃月刀, 赤兔马)
    - Title: 官职/爵位 (如：汉中王, 丞相)
    - Event: 具体事件 (如：桃园结义, 三顾茅庐)

    需要提取的关系：实体间的互动 (如：出生地、参与战役、拥有武器、任职于、发生在等)。

    **输出要求**：
    1. 必须且只能输出一个标准的 JSON 对象。
    2. 格式如下：
    {{
        "entities": [
            {{"name": "实体名", "type": "实体类型"}}
        ],
        "relations": [
            {{"head": "实体A", "head_type": "类型A", "relation": "关系描述", "tail": "实体B", "tail_type": "类型B"}}
        ]
    }}
    3. 如果片段中没有相关内容，返回 {{ "entities": [], "relations": [] }}。
    4. 不要输出 markdown 标记 (```) 或任何解释文字。

    文本片段：
    {chunk}
    """

    try:
        response = client.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 2048}
            },
            timeout=90.0
        )
        response.raise_for_status()
        content = response.json().get("response", "")

        # 清洗 JSON 字符串
        content = content.replace("```json", "").replace("```", "").strip()
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1:
            content = content[start:end + 1]
        else:
            return {"entities": [], "relations": []}

        return json.loads(content)
    except Exception as e:
        print(f"Error processing chunk: {e}")
        return {"entities": [], "relations": []}


def main():
    if not os.path.exists(INPUT_FILE):
        print(f"错误：找不到输入文件 {INPUT_FILE}")
        return

    print(f"正在读取 {INPUT_FILE} ...")
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        text = f.read()

    chunks = split_text(text, CHUNK_SIZE)
    all_entities = []
    all_relations = []

    print(f"开始提取丰富实体，共 {len(chunks)} 个片段...")

    with httpx.Client() as client:
        for chunk in tqdm(chunks, desc="Extracting Rich Entities"):
            result = extract_chunk(chunk, client)
            all_entities.extend(result.get("entities", []))
            all_relations.extend(result.get("relations", []))

    # 保存结果
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    output_data = {
        "entities": all_entities,
        "relations": all_relations
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"✅ 提取完成！")
    print(f"   - 实体总数：{len(all_entities)}")
    print(f"   - 关系总数：{len(all_relations)}")
    print(f"结果已保存至：{OUTPUT_FILE}")


if __name__ == "__main__":
    main()