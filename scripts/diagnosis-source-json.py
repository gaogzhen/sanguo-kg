import json
import os.path
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
file_path = os.path.join(DATA_DIR, "cleaned_rich_kg.json")  # 确认您的文件路径
try:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"📊 数据概览:")
    print(f"   - 实体数量 (entities): {len(data.get('entities', []))}")
    print(f"   - 关系数量 (relations): {len(data.get('relations', []))}")

    if len(data.get('relations', [])) == 0:
        print("\n❌ 确诊：关系列表为空！需要重新提取关系。")
        # 打印前两个实体的结构，检查是否有隐藏的 relations
        if len(data.get('entities', [])) > 0:
            print(f"   - 第一个实体样例: {data['entities'][0]}")
    else:
        print("\n✅ 数据中有关系，可能是导入脚本的字段名不匹配。")
        print(f"   - 第一条关系样例: {data['relations'][0]}")

except FileNotFoundError:
    print(f"❌ 文件未找到: {file_path}")
except json.JSONDecodeError:
    print("❌ JSON 文件格式错误，文件可能已损坏。")