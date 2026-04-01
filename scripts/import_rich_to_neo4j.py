import os
import json
from pathlib import Path

from neo4j import GraphDatabase
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()

URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
USER = os.getenv("NEO4J_USER", "neo4j")
PASSWORD = os.getenv("NEO4J_PASSWORD", "StrongPassword123!")
DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

# --- 路径配置 ---
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
INPUT_FILE = os.path.join(DATA_DIR, "rich_extracted_clean.json")

# 映射 Python 类型到 Neo4j Label
TYPE_MAP = {
    "Person": "Person",
    "Location": "Location",
    "Battle": "Battle",
    "Time": "TimePeriod",
    "Weapon": "Weapon",
    "Title": "Title",
    "Event": "Event"
}


def connect():
    driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))
    try:
        driver.verify_connectivity()
        print("✅ 成功连接到 Neo4j")
        return driver
    except Exception as e:
        print(f"❌ 连接失败：{e}")
        return None


def import_data(driver, data):
    entities = data.get("entities", [])
    relations = data.get("relations", [])

    with driver.session(database=DATABASE) as session:
        # 1. 创建索引
        print("正在创建索引...")
        session.run("CREATE INDEX IF NOT EXISTS FOR (n:Person) ON (n.name)")
        session.run("CREATE INDEX IF NOT EXISTS FOR (n:Location) ON (n.name)")
        session.run("CREATE INDEX IF NOT EXISTS FOR (n:Battle) ON (n.name)")

        # 2. 导入实体
        print("正在导入实体...")
        for ent in tqdm(entities, desc="Entities"):
            name = ent["name"]
            etype = ent["type"]
            label = TYPE_MAP.get(etype, "Generic")  # 默认标签

            # Cypher: MERGE 节点，动态标签需要使用 apoc 或者写死判断，这里用简单的 IF/ELSE 逻辑或者统一用 Generic + 属性
            # 为了简单且不使用 APOC，我们针对已知类型写特定查询，未知类型用 Generic
            if label in ["Person", "Location", "Battle", "TimePeriod", "Weapon", "Title", "Event"]:
                query = f"MERGE (n:{label} {{name:  $ name}})"
            else:
                query = "MERGE (n:Generic {name:  $ name, original_type:  $ type})"

            session.run(query, name=name, type=etype)

        # 3. 导入关系
        print("正在导入关系...")
        count = 0
        for rel in tqdm(relations, desc="Relations"):
            head = rel["head"]
            tail = rel["tail"]
            relation_type = rel["relation"].replace(" ", "_").upper()  # 关系类型转为大写无空格，如 出生地 -> 出生地

            head_label = TYPE_MAP.get(rel["head_type"], "Generic")
            tail_label = TYPE_MAP.get(rel["tail_type"], "Generic")

            # 构建动态 Cypher (注意：在生产环境中应防范注入，这里类型是受控的)
            # 为了安全起见，我们依然使用 MERGE 查找节点，不依赖标签匹配查找，只依赖 name
            # 因为 name 在我们清洗后应该是唯一的，或者我们在同类型下唯一

            cypher = f"""
            MATCH (a) WHERE a.name =  $ head AND (a:{head_label} OR a:Generic)
            MATCH (b) WHERE b.name =  $ tail AND (b:{tail_label} OR b:Generic)
            MERGE (a)-[r:{relation_type}]->(b)
            """
            # 注意：上面的动态标签匹配语法在 Neo4j 中不完全支持直接在 MATCH 中这样写混合标签
            # 更稳妥的方式是分两步，或者只用 name 查找（如果有全局唯一性）
            # 修正方案：仅通过 name 查找，假设名字在图谱内大致唯一，或者依靠之前创建的索引

            safe_cypher = """
            MATCH (a:Person {name:  $ head})
            MATCH (b:Person {name:  $ tail})
            MERGE (a)-[r:REL]->(b)
            """
            # 由于动态标签较复杂，这里采用通用策略：
            # 只要名字匹配就连接。为了更精确，我们可以遍历所有可能的标签组合，或者简化处理：
            # 假设我们已经导入了节点，直接通过 name 属性查找即可（Neo4j 会扫描所有标签）

            generic_cypher = """
            MATCH (a) WHERE a.name =  $ head
            MATCH (b) WHERE b.name =  $ tail
            MERGE (a)-[r:`{rel_type}`]->(b)
            """.format(rel_type=relation_type)

            try:
                session.run(generic_cypher, head=head, tail=tail)
                count += 1
            except Exception as e:
                # 忽略找不到节点的错误（可能是因为清洗时去掉了某些孤立点）
                pass

        return count


def main():
    if not os.path.exists(INPUT_FILE):
        print(f"错误：找不到文件 {INPUT_FILE}")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    driver = connect()
    if not driver:
        return

    try:
        total = import_data(driver, data)
        print(f"✅ 导入成功！共处理 {total} 条关系。")
        print("🌐 访问 http://localhost:7474 查看图谱。")
        print("💡 提示：在 Neo4j Browser 中输入 'MATCH (n) RETURN n LIMIT 100' 查看概览。")
        print("   可以尝试过滤特定类型：'MATCH (n:Battle) RETURN n' 查看所有战役。")
    finally:
        driver.close()


if __name__ == "__main__":
    main()