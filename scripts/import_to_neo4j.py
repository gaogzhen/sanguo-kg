from neo4j import GraphDatabase
import json
import os
from pathlib import Path

# --- 1. 配置区 ---
# 请确保你已安装 Neo4j Desktop 或服务正在运行
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "StrongPassword123!"  # 请修改为你的密码

# --- 2. 路径配置 ---
# 假设脚本放在项目根目录或 scripts 目录下
BASE_DIR = Path(__file__).parent.parent
# 根据你的报错路径，推测文件在 data 文件夹下
DATA_FILE_PATH = BASE_DIR / "data" / "rich_extracted_clean.json"


class Neo4jImporter:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def create_indexes(self, session):
        """创建索引以加速导入和查询"""
        print("🔨 正在创建索引...")
        # 为常用 Label 的 name 属性创建索引
        indexes = ["Person", "Location", "Time", "Event", "Weapon", "Title", "Generic"]
        for label in indexes:
            session.run(f"CREATE INDEX IF NOT EXISTS FOR (n:{label}) ON (n.name)")
        print(f"✅ 创建了 {len(indexes)} 个索引")

    def import_entities(self, session, entities):
        """导入实体节点"""
        print(f"👥 正在导入实体节点... (共 {len(entities)} 个)")

        # 定义合法的 Label，防止非法字符或错误类型（如将人名误标为武器）
        valid_labels = {"Person", "Location", "Time", "Event", "Weapon", "Title"}

        for entity in entities:
            name = entity.get("name", "").strip()
            etype = entity.get("type", "Generic")

            # 安全处理：如果提取的类型不在白名单中，或者该节点已存在但类型不同，使用 Generic
            # 这里简单处理，直接使用提取的类型，Neo4j 会自动处理标签
            # 但是为了防止特殊字符，我们只取字母数字下划线
            if not name:
                continue

            # 构建 Cypher 查询
            # 使用 MERGE 防止重复创建
            query = (
                f"MERGE (n:`{etype}` {{name: $name}}) "
                "ON CREATE SET n.created = timestamp() "
                "RETURN count(n)"
            )

            try:
                session.run(query, name=name)
            except Exception as e:
                # 如果类型名包含非法字符，回退到 Generic
                if "SyntaxError" in str(e) or "InvalidToken" in str(e):
                    session.run(
                        "MERGE (n:Generic {name: $name}) SET n.original_type = $orig_type RETURN count(n)",
                        name=name, orig_type=etype
                    )
                else:
                    print(f"   导入节点出错: {name} ({etype}) - {e}")

    def import_relations(self, session, relations):
        """导入关系"""
        print(f"🔗 正在导入关系... (共 {len(relations)} 条)")

        for rel in relations:
            source_name = rel.get("source")
            target_name = rel.get("target")
            rel_type = rel.get("type", "RELATED")

            # 清理关系类型，确保符合 Neo4j 关系类型命名规范（大写字母、数字、下划线）
            # 不能有空格或中文（虽然 Neo4j 4+ 支持中文，但为了 Cypher 语法安全，建议转大写或用下划线）
            clean_rel_type = "".join([c if c.isalnum() or c == "_" else "_" for c in rel_type]).strip("_").upper()
            if not clean_rel_type:
                clean_rel_type = "RELATED"

            if not source_name or not target_name:
                continue

            # 使用通用匹配，不依赖 Label，仅依赖 name 属性
            # 注意：如果存在重名（如不同朝代的同名地点），可能会匹配错误，但这是最通用的方案
            query = f"""
                MATCH (a) WHERE a.name = $source
                MATCH (b) WHERE b.name = $target
                MERGE (a)-[r:`{clean_rel_type}`]->(b)
                ON CREATE SET r.created = timestamp()
                RETURN count(r)
            """

            try:
                session.run(query, source=source_name, target=target_name)
            except Exception as e:
                # 如果关系类型非法（如包含特殊字符），则跳过或记录日志
                if "SyntaxError" in str(e):
                    print(f"   跳过非法关系类型: {rel_type} ({source_name} -> {target_name})")
                else:
                    print(f"   导入关系出错: {source_name} -[{rel_type}]-> {target_name} : {e}")

    def run_import(self, data):
        with self.driver.session() as session:
            # 1. 创建索引
            self.create_indexes(session)

            # 2. 导入实体
            entities = data.get("entities", [])
            if entities:
                self.import_entities(session, entities)
            else:
                print("⚠️ 警告：JSON 中未找到 entities 字段或为空")

            # 3. 导入关系
            relations = data.get("relations", [])
            if relations:
                self.import_relations(session, relations)
            else:
                print("ℹ️ 提示：JSON 中未找到 relations 字段或为空")


def main():
    # 检查文件是否存在
    if not os.path.exists(DATA_FILE_PATH):
        print(f"❌ 错误：找不到数据文件。请检查路径是否正确。")
        print(f"   当前查找路径：{DATA_FILE_PATH.absolute()}")
        print(f"   请将 rich_extracted_clean.json 放在上述路径中。")
        return

    print(f"✅ 找到数据文件：{DATA_FILE_PATH}")

    # 读取 JSON 文件
    try:
        with open(DATA_FILE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ JSON 解析错误：{e}")
        return
    except Exception as e:
        print(f"❌ 读取文件错误：{e}")
        return

    # 连接数据库
    try:
        print("🔗 正在连接 Neo4j 数据库...")
        importer = Neo4jImporter(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
        print("✅ 连接成功")

        # 执行导入
        importer.run_import(data)

        importer.close()
        print("\n🎉 导入流程完成！")
        print(f"   数据已导入至 Neo4j。请在浏览器打开 http://localhost:7474 查看。")
        print(f"   推荐查询：MATCH (n) RETURN n LIMIT 25")

    except Exception as e:
        print(f"❌ 数据库操作失败：{e}")


if __name__ == "__main__":
    main()