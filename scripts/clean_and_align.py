import json
import re
from pathlib import Path
from collections import defaultdict

# --- 配置 ---
BASE_DIR = Path(__file__).parent.parent
INPUT_FILE = BASE_DIR / "data" / "rich_extracted.json"  # 输入：有关系的文件
OUTPUT_FILE = BASE_DIR / "data" / "rich_extracted_clean.json"  # 输出：清洗后的文件


def load_data():
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def normalize_name(name):
    """
    简单的名称标准化规则
    可以根据需要在此处添加更多规则
    """
    if not name: return ""
    # 去除前后空格
    name = name.strip()
    # 去除称呼后缀 (可选，视你的提取情况而定)
    # 例如：如果提取的是 "刘备将军"，这里可以试着去掉 "将军"
    suffixes = ["将军", "大人", "主公", "丞相", "太守", "之", "的"]
    for suffix in suffixes:
        if name.endswith(suffix) and len(name) > len(suffix) + 1:
            # 简单判断，防止误删（如 "关云长" 的 "长"）
            if suffix not in ["之", "的"]:
                name = name[:-len(suffix)]
    return name


def clean_data(data):
    entities = data.get('entities', [])
    relations = data.get('relations', [])

    print(f"📊 原始数据: {len(entities)} 实体, {len(relations)} 关系")

    # 1. 建立实体名称映射表 (别名 -> 标准名)
    # 我们假设 JSON 中的 "name" 字段是标准名
    # 同时，我们收集所有实体的标准名到一个集合中，用于快速查找
    standard_names = set()
    name_mapping = {}  # 记录所有出现过的名称变体

    for entity in entities:
        name = entity.get('name', '').strip()
        if name:
            standard_names.add(name)
            # 这里可以扩展：如果你有别名数据，可以在这里建立映射
            # 例如：name_mapping["玄德"] = "刘备"

    # 2. 清洗关系
    valid_relations = []
    removed_count = 0
    fixed_count = 0

    for rel in relations:
        src_raw = rel.get('source', '').strip()
        tgt_raw = rel.get('target', '').strip()
        rel_type = rel.get('type', 'Unknown')

        if not src_raw or not tgt_raw:
            removed_count += 1
            continue

        # --- 核心修复逻辑 ---

        # 尝试 1: 直接匹配
        src_found = src_raw in standard_names
        tgt_found = tgt_raw in standard_names

        # 尝试 2: 标准化后匹配 (如果直接匹配失败)
        src_norm = normalize_name(src_raw)
        tgt_norm = normalize_name(tgt_raw)

        if not src_found and src_norm in standard_names:
            src_raw = src_norm  # 修正为列表中的标准名
            src_found = True
            fixed_count += 1

        if not tgt_found and tgt_norm in standard_names:
            tgt_raw = tgt_norm  # 修正为列表中的标准名
            tgt_found = True
            fixed_count += 1

        # 最终检查：如果两端实体都存在（或我们决定宽容处理），则保留
        # 这里采用宽容策略：只要不是完全乱码，就保留，即使实体不在列表中
        # 因为 Neo4j 可以自动创建缺失的节点
        if src_raw and tgt_raw:
            valid_relations.append({
                "source": src_raw,
                "target": tgt_raw,
                "type": rel_type
            })
        else:
            removed_count += 1

    print(f"✅ 清洗完成:")
    print(f"   - 修复名称: {fixed_count} 条")
    print(f"   - 移除无效: {removed_count} 条")
    print(f"   - 最终关系: {len(valid_relations)} 条")

    return {
        "entities": entities,
        "relations": valid_relations
    }


def main():
    if not INPUT_FILE.exists():
        print(f"❌ 找不到文件: {INPUT_FILE}")
        return

    print(f"📖 读取: {INPUT_FILE}")
    data = load_data()

    cleaned_data = clean_data(data)

    print(f"💾 保存至: {OUTPUT_FILE}")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(cleaned_data, f, ensure_ascii=False, indent=2)

    print("🎉 完成！请使用新生成的文件进行导入。")


if __name__ == "__main__":
    main()