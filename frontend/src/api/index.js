import axios from 'axios';

// 创建 axios 实例
const request = axios.create({
    baseURL: 'http://127.0.0.1:8000', // 对应 FastAPI 的地址
    timeout: 10000 // 超时时间 10秒
});

// 导出 API 方法
export const api = {
    // 获取图谱数据
    getGraphData: (center, limit) => {
        return request.get('/api/graph', { params: { center, limit } });
    },
    // 智能问答
    chat: (question) => {
        return request.post('/api/chat', { question });
    },
    // 获取统计数据
    getStats: () => {
        return request.get('/api/stats');
    },
    // 搜索节点
    searchNode: (keyword) => {
        return request.post('/api/search', { keyword, limit: 10 });
    }
};