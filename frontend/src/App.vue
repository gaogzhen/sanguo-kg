<template>
  <div class="app-container">
    <!-- 顶部导航 -->
    <header class="header">
      <h1>三国演义 · 知识图谱沙盘</h1>
      <div class="search-box">
        <input v-model="searchKeyword" placeholder="搜索人物..." @keyup.enter="handleSearch" />
        <button @click="handleSearch">搜索</button>
      </div>
    </header>

    <!-- 主要内容区 -->
    <main class="main-content">
      <!-- 左侧：图谱 (占 70%) -->
      <section class="graph-section">
        <KGGraph ref="graphRef" />
      </section>

      <!-- 右侧：问答与统计 (占 30%) -->
      <aside class="sidebar">
        <div class="chat-section">
          <ChatBox />
        </div>
      </aside>
    </main>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import KGGraph from './components/KGGraph.vue';
import ChatBox from './components/ChatBox.vue';
import { api } from './api';

const graphRef = ref(null);
const searchKeyword = ref('');

const handleSearch = async () => {
  if (!searchKeyword.value) return;
  
  // 1. 调用搜索接口
  const res = await api.searchNode(searchKeyword.value);
  if (res.data.length > 0) {
    // 2. 找到第一个结果，重新加载图谱中心
    const targetName = res.data[0].name;
    graphRef.value.fetchData(targetName);
    alert(`已定位到：${targetName}`);
  } else {
    alert('未找到相关人物');
  }
};
</script>

<style>
/* 全局重置 */
body { margin: 0; padding: 0; font-family: 'Microsoft YaHei', sans-serif; background: #121212; color: #fff; overflow: hidden; }
.app-container { display: flex; flex-direction: column; height: 100vh; }

/* 头部样式 */
.header {
  height: 60px;
  background: #1f1f1f;
  display: flex;
  align-items: center;
  padding: 0 20px;
  justify-content: space-between;
  box-shadow: 0 2px 10px rgba(0,0,0,0.5);
  z-index: 10;
}
.header h1 { margin: 0; font-size: 24px; color: #f39c12; letter-spacing: 1px; }
.search-box { display: flex; gap: 10px; }
.search-box input { padding: 8px; border-radius: 4px; border: 1px solid #444; background: #333; color: #fff; }
.search-box button { padding: 8px 15px; background: #f39c12; border: none; border-radius: 4px; cursor: pointer; color: #000; font-weight: bold; }

/* 主体布局 */
.main-content { flex: 1; display: flex; padding: 10px; gap: 10px; overflow: hidden; }
.graph-section { flex: 7; height: 100%; } /* 70% 宽度 */
.sidebar { flex: 3; display: flex; flex-direction: column; gap: 10px; height: 100%; } /* 30% 宽度 */
.chat-section { flex: 1; height: 100%; }
</style>