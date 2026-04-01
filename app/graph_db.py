from neo4j import GraphDatabase
from typing import List, Dict, Any


class Neo4jConnection:
    def __init__(self, uri: str, user: str, password: str):
        self.uri = uri
        self.user = user
        self.password = password
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

        # 验证连接
        try:
            self.driver.verify_connectivity()
            print("✅ Neo4j 连接成功")
        except Exception as e:
            print(f"❌ Neo4j 连接失败: {e}")

    def close(self):
        self.driver.close()

    # --- 核心查询方法 ---

    def get_neighbors(self, center_node_name: str, depth: int = 1, limit: int = 100) -> Dict[str, List]:
        """
        获取中心节点的邻居
        修复：通过 Python f-string 将深度直接写入 Cypher 语句，避免参数化报错
        """
        with self.driver.session() as session:
            # ✅ 修复点：使用 f-string 将 depth 变量直接拼接到查询字符串中
            # 注意：depth 是整数，直接拼接是安全的
            cypher_query = f"""
            MATCH (n:Person {{name: $name}})
            MATCH path = (n)-[r*1..{depth}]-(m)
            RETURN n, r, m
            LIMIT $limit
            """

            # 参数只传递 name 和 limit
            result = session.run(cypher_query, name=center_node_name, limit=limit)

            nodes = {}
            links = []

            for record in result:
                # 处理节点 n (中心节点)
                n = record['n']
                self._add_node(nodes, n)

                # 处理节点 m (邻居节点)
                m = record['m']
                self._add_node(nodes, m)

                # 处理关系 r
                # 注意：当 depth > 1 时，r 可能是一个关系列表（路径），这里简化处理
                rel = record['r']

                if isinstance(rel, list):
                    # 如果是多跳路径 (depth > 1)，rel 是列表
                    # 这里简单取路径的第一段关系作为展示，或者你可以遍历整个路径
                    if len(rel) > 0:
                        r = rel[0]
                        links.append({
                            "source": n['name'],
                            "target": m['name'],  # 注意：多跳时 m 是路径终点，这里逻辑可能需要根据需求微调
                            "label": list(r.type)[0]
                        })
                else:
                    # 单跳路径 (depth = 1)，rel 是单个关系
                    links.append({
                        "source": n['name'],
                        "target": m['name'],
                        "label": list(rel.type)[0]
                    })

            return {"nodes": list(nodes.values()), "links": links}

    def search_nodes(self, keyword: str, limit: int = 10) -> List[Dict]:
        """
        模糊搜索节点
        """
        with self.driver.session() as session:
            query = """
            MATCH (n) 
            WHERE n.name CONTAINS $keyword
            RETURN n.name as name, labels(n)[0] as type
            LIMIT $limit
            """
            result = session.run(query, keyword=keyword, limit=limit)
            return [record.data() for record in result]

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取图谱统计信息
        """
        with self.driver.session() as session:
            # 统计节点总数
            count_nodes = session.run("MATCH (n) RETURN count(n) as count").single()["count"]
            # 统计关系总数
            count_rels = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()["count"]

            # 统计各类别数量
            label_query = """
            MATCH (n)
            UNWIND labels(n) as label
            RETURN label, count(n) as count
            ORDER BY count DESC
            """
            label_result = session.run(label_query)
            distribution = [{"label": r["label"], "count": r["count"]} for r in label_result]

            return {
                "total_nodes": count_nodes,
                "total_relations": count_rels,
                "category_distribution": distribution
            }

    # --- 内部辅助方法 ---

    def _add_node(self, nodes_dict: dict, node_record):
        """辅助方法：去重添加节点"""
        name = node_record['name']
        if name not in nodes_dict:
            labels = list(node_record.labels)
            # 默认取第一个标签作为分类，如果没有标签则为 'Thing'
            category = labels[0] if labels else 'Thing'

            # 设置节点大小规则
            size = 40 if category == 'Person' else 25

            nodes_dict[name] = {
                "id": name,
                "name": name,
                "category": category,
                "symbolSize": size
            }