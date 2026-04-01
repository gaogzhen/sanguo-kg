<template>
  <div id="graph-container" ref="graphRef"></div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue';
import * as echarts from 'echarts';
import { api } from '../api';

const graphRef = ref(null);
let myChart = null;

// 初始化图表
const initChart = () => {
  if (!graphRef.value) return;
  myChart = echarts.init(graphRef.value);
  
  // 窗口大小改变时重绘
  window.addEventListener('resize', () => myChart.resize());
};

// 获取并渲染数据
const fetchData = async (centerNode = '刘备') => {
  try {
    const res = await api.getGraphData(centerNode, 100);
    const data = res.data;
    
    // 处理数据格式适配 ECharts
    // 1. 节点处理
    const nodes = data.nodes.map(node => ({
      ...node,
      // 根据类别设置颜色
      itemStyle: {
        color: getCategoryColor(node.category)
      },
      // 标签显示
      label: { show: true, position: 'right', color: '#fff' }
    }));

    // 2. 关系处理
    const links = data.links.map(link => ({
      ...link,
      // 关系线上的文字
      label: { show: true, formatter: '{b}', color: '#aaa', fontSize: 10 }
    }));

    // 3. 配置项
    const option = {
      tooltip: {
        trigger: 'item',
        formatter: (params) => {
            if (params.dataType === 'node') return `<b>${params.name}</b><br/>${params.data.category}`;
            return `${params.data.source} ➜ ${params.data.target}`;
        }
      },
      series: [
        {
          type: 'graph',
          layout: 'force', // 力导向布局
          data: nodes,
          links: links,
          categories: [], // 可以添加图例
          roam: true, // 开启鼠标缩放和平移
          draggable: true, // 节点可拖拽
          labelLayout: { hideOverlap: true }, // 避免标签重叠
          force: {
            repulsion: 200, // 节点排斥力，越大越散
            edgeLength: 60, // 边的长度
            gravity: 0.1    // 引力，防止飞出画布
          },
          lineStyle: {
            color: 'source',
            curveness: 0.3, // 曲线弯曲度
            width: 1.5
          },
          emphasis: {
            focus: 'adjacency', // 高亮邻接节点
            lineStyle: { width: 4 }
          }
        }
      ]
    };

    myChart.setOption(option);
  } catch (error) {
    console.error("图谱数据加载失败", error);
  }
};

// 简单的颜色映射
const getCategoryColor = (category) => {
  const colors = {
    'Person': '#f39c12', // 金色
    'Location': '#3498db', // 蓝色
    'Battle': '#e74c3c', // 红色
    'Weapon': '#9b59b6' // 紫色
  };
  return colors[category] || '#2ecc71';
};

// 暴露方法给父组件
defineExpose({ fetchData });

onMounted(() => {
  initChart();
  fetchData(); // 默认加载刘备
});
</script>

<style scoped>
#graph-container {
  width: 100%;
  height: 100%;
  background-color: #1a1a1a; /* 深色背景 */
  border-radius: 8px;
}
</style>