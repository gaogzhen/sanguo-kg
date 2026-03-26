import os
import json
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

INPUT_FILE = DATA_DIR / "rich_extracted.json"
OUTPUT_FILE = DATA_DIR / "cleaned_rich_kg.json"

# 别名映射 (扩展版)
ALIAS_MAP = {
    # 人物
    "关云长": "关羽", "美髯公": "关羽", "汉寿亭侯": "关羽",
    "玄德": "刘备", "刘玄德": "刘备", "皇叔": "刘备",
    "孟德": "曹操", "曹孟德": "曹操", "魏王": "曹操",
    "孔明": "诸葛亮", "诸葛孔明": "诸葛亮", "卧龙": "诸葛亮",
    "奉孝": "郭嘉", "子龙": "赵云", "赵子龙": "赵云",
    "翼德": "张飞", "张翼德": "张飞",
    # 地点
    "荆楚": "荆州", "建业": "南京", "许昌": "许都",
    # 战役
    "赤壁大战": "赤壁之战", "官渡大战": "官渡之战"
}

# 关系标准化映射
RELATION_NORMALIZE = {
    "出生在": "出生地", "生于": "出生地", "家乡是": "出生地",
    "参与了": "参与战役", "参加": "参与战役", "打赢了": "胜利战役",
    "拥有": "持有", "武器是": "持有", "坐骑是": "持有",
    "任职": "担任官职", "官拜": "担任官职", "封为": "担任官职",
    "发生在": "发生地点", "地点是": "发生地点",
    "时间是": "发生时间", "发生于": "发生时间"
}


def normalize_name(name, entity_type):
    name = name.strip()
    # 简单策略：优先匹配别名表，如果没有则保留原名
    # 实际项目中可根据 entity_type 加载不同的别名表
    return ALIAS_MAP.get(name, name)


def normalize_relation(rel):
    rel = rel.strip()
    for key, value in RELATION_NORMALIZE.items():
        if key in rel or rel == key:
            return value
    return rel


def main():
    if not os.path.exists(INPUT_FILE):
        print(f"错误：找不到文件 {INPUT_FILE}")
        return

    print("正在加载原始数据...")
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    raw_entities = data.get("entities", [])
    raw_relations = data.get("relations", [])

    # 1. 清洗实体 (去重 + 别名合并)
    unique_entities = {}  # key: (name, type), value: final_name
    cleaned_entities_list = []

    for ent in raw_entities:
        name = ent.get("name", "").strip()
        etype = ent.get("type", "Unknown").strip()
        if not name: continue

        final_name = normalize_name(name, etype)
        key = (final_name, etype)

        if key not in unique_entities:
            unique_entities[key] = True
            cleaned_entities_list.append({"name": final_name, "type": etype})

    # 2. 清洗关系
    cleaned_relations = []
    seen_relations = set()

    for rel in raw_relations:
        head = normalize_name(rel.get("head", ""), rel.get("head_type", ""))
        tail = normalize_name(rel.get("tail", ""), rel.get("tail_type", ""))
        relation = normalize_relation(rel.get("relation", ""))
        head_type = rel.get("head_type", "Unknown")
        tail_type = rel.get("tail_type", "Unknown")

        if not head or not tail or head == tail:
            continue

        # 更新关系中的实体名称以匹配清洗后的实体
        # (注意：这里假设别名映射是一对一的，直接替换即可)

        r_key = (head, relation, tail)
        if r_key not in seen_relations:
            seen_relations.add(r_key)
            cleaned_relations.append({
                "head": head,
                "head_type": head_type,
                "relation": relation,
                "tail": tail,
                "tail_type": tail_type
            })

    # 保存
    output_data = {
        "entities": cleaned_entities_list,
        "relations": cleaned_relations
    }

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"✅ 清洗完成！")
    print(f"   - 实体：{len(raw_entities)} -> {len(cleaned_entities_list)}")
    print(f"   - 关系：{len(raw_relations)} -> {len(cleaned_relations)}")
    print(f"结果已保存至：{OUTPUT_FILE}")


if __name__ == "__main__":
    main()