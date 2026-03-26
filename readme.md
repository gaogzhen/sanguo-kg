# 🏮 三国知识图谱智能问答系统 (Sanguo KG QA)

基于 **Neo4j** 图数据库、**FastAPI** 后端、**Vue3** 前端以及 **Ollama (Qwen2.5)** 大模型的本地化智能问答系统。
本项目核心特色是能够直接从《三国演义》原始文本（.txt）中，利用 LLM 自动提取实体与关系，构建动态知识图谱。

## 🚀 核心特性
- **文本转图谱 (Text-to-Graph)**: 内置自动化脚本，利用本地 LLM 从 `三国演义.txt` 提取人物、关系和事件，无需手动录入。
- **混合开发架构**: Neo4j 运行于 Docker，后端/前端/Ollama 本地运行，支持 VS Code 断点调试与热重载。
- **RAG + Graph**: 结合图数据库检索与大模型推理，提供精准的“基于原文”的历史问答。
- **Windows 优化**: 专为 Windows PowerShell 环境配置，解决脚本执行策略问题。

## 🛠️ 技术栈
- **数据源**: 《三国演义》纯文本 (.txt)
- **数据库**: Neo4j 5.15 (Docker) + APOC Plugin
- **AI 引擎**: Ollama (Qwen2.5-7B) - 用于信息抽取 (IE) 和问答
- **后端**: Python 3.12, FastAPI, Uvicorn, Neo4j Driver, Httpx
- **前端**: Vue 3, Vite, Element Plus, ECharts (图谱可视化)
- **开发工具**: VS Code, Docker Desktop, PowerShell

## 📋 前置要求
1. **Python 3.10+**: [下载链接](https://www.python.org/downloads/)
2. **Node.js 18+**: [下载链接](https://nodejs.org/)
3. **Docker Desktop**: 确保 WSL 2 后端已启用。
4. **Ollama**: 
   - 安装: `winget install Ollama.Ollama`
   - **关键配置**: 设置系统环境变量 `OLLAMA_HOST=0.0.0.0` 并重启 Ollama 服务。
   - 拉取模型: `ollama pull qwen2.5:7b`

## ⚡ 快速开始 (Windows)

### 1. 启动基础设施 (Neo4j)
```powershell
# 临时解除脚本执行限制 (仅当前窗口)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
# 启动数据库
docker compose -f docker-compose.dev.yml up -d