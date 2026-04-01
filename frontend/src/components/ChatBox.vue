<template>
  <div class="chat-container">
    <div class="chat-header">AI 军师 (基于图谱问答)</div>
    <div class="chat-messages" ref="msgContainer">
      <div v-for="(msg, index) in messages" :key="index" 
           :class="['message', msg.role]">
        <div class="bubble">{{ msg.content }}</div>
      </div>
      <div v-if="loading" class="message ai">
        <div class="bubble loading">思考中...</div>
      </div>
    </div>
    <div class="chat-input">
      <input v-model="inputText" @keyup.enter="sendMessage" placeholder="问点啥？比如：刘备手下有哪些大将？" />
      <button @click="sendMessage">发送</button>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue';
import { api } from '../api';

const messages = ref([
  { role: 'ai', content: '你好！我是三国知识图谱助手，请问有什么可以帮你？' }
]);
const inputText = ref('');
const loading = ref(false);
const msgContainer = ref(null);

const sendMessage = async () => {
  if (!inputText.value.trim()) return;

  // 添加用户消息
  messages.value.push({ role: 'user', content: inputText.value });
  const question = inputText.value;
  inputText.value = '';
  loading.value = true;

  // 滚动到底部
  nextTick(() => {
    if(msgContainer.value) msgContainer.value.scrollTop = msgContainer.value.scrollHeight;
  });

  try {
    const res = await api.chat(question);
    messages.value.push({ role: 'ai', content: res.data.answer });
  } catch (err) {
    messages.value.push({ role: 'ai', content: '抱歉，服务连接失败，请检查后端服务。' });
  } finally {
    loading.value = false;
    nextTick(() => {
        if(msgContainer.value) msgContainer.value.scrollTop = msgContainer.value.scrollHeight;
    });
  }
};
</script>

<style scoped>
.chat-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #2c2c2c;
  border-radius: 8px;
  overflow: hidden;
  color: #fff;
}
.chat-header { padding: 15px; background: #333; font-weight: bold; border-bottom: 1px solid #444; }
.chat-messages { flex: 1; padding: 15px; overflow-y: auto; display: flex; flex-direction: column; gap: 10px; }
.message { display: flex; }
.message.user { justify-content: flex-end; }
.message.ai { justify-content: flex-start; }
.bubble { padding: 10px 15px; border-radius: 8px; max-width: 80%; line-height: 1.5; }
.message.user .bubble { background: #3498db; color: #fff; }
.message.ai .bubble { background: #444; color: #eee; }
.chat-input { display: flex; padding: 15px; border-top: 1px solid #444; }
.chat-input input { flex: 1; padding: 10px; border-radius: 4px; border: none; outline: none; }
.chat-input button { margin-left: 10px; padding: 10px 20px; background: #f39c12; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; }
</style>