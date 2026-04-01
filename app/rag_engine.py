from typing import List

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

# 引入之前写的数据库连接类
from graph_db import Neo4jConnection


class SanguoRAG:
    def __init__(self, db: Neo4jConnection):
        self.db = db

        # 1. 初始化 Ollama 模型
        # 确保本地 Ollama 已运行: ollama run qwen:7b (或 llama3)
        self.llm = ChatOllama(
            model="qwen2.5:7b",
            temperature=0,
            base_url="http://localhost:11434"
        )

        # 2. 定义提示词 (Prompt Templates)

        # --- 步骤 A: 实体提取提示词 ---
        # 作用：把 "刘备是谁？" 转化为 ["刘备"]
        self.extraction_prompt = ChatPromptTemplate.from_messages([
            ("system", "你是一个三国知识图谱的查询助手。请从用户的问题中提取所有提到的人物名称或地点。"
                       "只返回名称，用逗号分隔。如果没有具体名称，返回'无'。"),
            ("human", "{question}")
        ])

        # --- 步骤 B: 最终回答提示词 ---
        # 作用：结合图谱数据回答问题
        self.generation_prompt = ChatPromptTemplate.from_messages([
            ("system", "你是一个精通《三国演义》的专家。请根据下方的【参考信息】回答用户的问题。"
                       "如果【参考信息】为空或不足以回答问题，请根据你的通用知识库回答，但语气要像讲故事一样。"),
            ("human", "【参考信息】:\n{context}\n\n用户问题: {question}")
        ])

    def _extract_entities(self, question: str) -> List[str]:
        """调用 LLM 提取实体名称"""
        # 构建提取链
        extraction_chain = self.extraction_prompt | self.llm | StrOutputParser()

        # 执行
        result = extraction_chain.invoke({"question": question})

        if "无" in result or not result.strip():
            return []

        # 简单的字符串清洗
        return [name.strip() for name in result.replace("，", ",").split(",") if name.strip()]

    def _retrieve_graph_data(self, entities: List[str]) -> str:
        """根据实体名称去 Neo4j 查询关系"""
        if not entities:
            return "未识别到具体实体。"

        context_parts = []

        # 遍历每个实体，查询其周围的一度关系
        for entity in entities:
            # 调用之前写的 graph_db 方法
            # limit=15 防止上下文太长超过 LLM 限制
            graph_data = self.db.get_neighbors(entity, depth=1, limit=15)

            links = graph_data.get('links', [])

            # 将关系格式化为自然语言文本
            # 格式：(刘备)--[统领]-->(关羽)
            for link in links:
                context_parts.append(f"({link['source']}) --[{link['label']}]--> ({link['target']})")

        # 去重并合并
        return "\n".join(list(set(context_parts)))

    def query(self, question: str) -> str:
        """
        主入口：处理用户问题
        """
        print(f"🔍 正在分析问题: {question}...")

        # 1. 提取实体 (例如: "刘备")
        entities = self._extract_entities(question)
        print(f"🏷️ 提取到的实体: {entities}")

        # 2. 检索图谱 (例如: 查询刘备的关系)
        print("📚 正在查询 Neo4j 知识图谱...")
        context = self._retrieve_graph_data(entities)
        print(f"📄 检索到的上下文:\n{context}")

        # 3. 生成回答
        print("🤖 正在生成回答...")

        # 构建生成链
        generation_chain = self.generation_prompt | self.llm | StrOutputParser()

        # 传入问题和检索到的上下文
        response = generation_chain.invoke({"question": question, "context": context})

        return response


# --- 测试代码 ---
if __name__ == "__main__":
    # 模拟数据库连接
    # db = Neo4jConnection("bolt://localhost:7687", "neo4j", "StrongPassword123!")
    # rag = SanguoRAG(db)
    # print(rag.query("刘备手下有哪些大将？"))
    pass