from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

# --- 请求模型 ---

class SearchRequest(BaseModel):
    """搜索请求模型"""
    keyword: str = Field(..., description="搜索关键词，例如人物名称")
    limit: int = Field(default=10, description="返回结果数量限制")

class ChatRequest(BaseModel):
    """智能问答请求模型"""
    question: str = Field(..., description="用户提出的自然语言问题")

# --- 响应模型 ---

class NodeItem(BaseModel):
    """图谱节点模型"""
    id: str = Field(..., description="节点唯一标识，通常是名称")
    name: str = Field(..., description="节点显示名称")
    category: str = Field(..., description="节点类型，如 Person, Location")
    symbolSize: int = Field(default=30, description="节点大小，用于前端渲染")
    # 允许额外字段，以容纳 Neo4j 节点的其他属性
    class Config:
        extra = "allow"

class LinkItem(BaseModel):
    """图谱关系模型"""
    source: str = Field(..., description="源节点名称")
    target: str = Field(..., description="目标节点名称")
    label: str = Field(..., description="关系类型")
    # 允许额外字段
    class Config:
        extra = "allow"

class GraphData(BaseModel):
    """图谱数据结构（ECharts 格式）"""
    nodes: List[NodeItem]
    links: List[LinkItem]

class StatItem(BaseModel):
    """统计项模型"""
    label: str
    count: int

class StatisticsResponse(BaseModel):
    """统计数据响应"""
    total_nodes: int
    total_relations: int
    category_distribution: List[StatItem]