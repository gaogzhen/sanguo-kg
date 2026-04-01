from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# 引入自定义模块
from graph_db import Neo4jConnection
from rag_engine import SanguoRAG

# --- 1. 初始化 FastAPI 应用 ---
# 这里定义了 'app' 变量，解决 Unresolved reference 问题
app = FastAPI(
    title="三国演义知识图谱系统",
    description="基于 Neo4j 和 Ollama 的智能问答与可视化系统",
    version="1.0.0"
)

# --- 2. 配置跨域 (CORS) ---
# 允许前端 (Vite/浏览器) 访问后端接口
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境建议限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 3. 数据库与 AI 初始化 ---
# 请确保 Neo4j 和 Ollama 正在运行
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "StrongPassword123!"  # 修改为你的密码

# 初始化数据库连接
db = Neo4jConnection(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)

# 初始化 RAG 引擎 (如果 Ollama 未启动，这里可能会报错，建议加 try-except)
try:
    rag_engine = SanguoRAG(db)
    print("✅ RAG 引擎初始化成功")
except Exception as e:
    print(f"⚠️ RAG 引擎初始化失败 (请检查 Ollama): {e}")
    rag_engine = None


# --- 4. 数据模型定义 ---
class ChatRequest(BaseModel):
    question: str


class SearchRequest(BaseModel):
    keyword: str
    limit: int = 10


# --- 5. API 路由 ---

@app.get("/")
def read_root():
    """API 根路径"""
    return {"message": "欢迎使用三国演义知识图谱 API", "status": "running"}


@app.get("/api/graph")
def get_graph(center: str = "刘备", limit: int = 50):
    """
    获取图谱数据
    :param center: 中心节点名称
    :param limit: 返回节点数量限制
    """
    try:
        data = db.get_neighbors(center, depth=1, limit=limit)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/search")
def search_nodes(req: SearchRequest):
    """搜索节点"""
    try:
        results = db.search_nodes(req.keyword, req.limit)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats")
def get_stats():
    """获取统计信息"""
    try:
        return db.get_statistics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat")
def chat_with_graph(req: ChatRequest):
    """
    智能问答接口
    """
    if not rag_engine:
        raise HTTPException(status_code=503, detail="AI 引擎未就绪，请检查 Ollama 服务")

    try:
        answer = rag_engine.query(req.question)
        return {"question": req.question, "answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- 6. 启动服务 ---
if __name__ == "__main__":
    import uvicorn

    # 启动 uvicorn 服务器
    # host="0.0.0.0" 允许局域网访问
    uvicorn.run(app, host="127.0.0.1", port=8000)