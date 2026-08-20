<template>
  <div class="ai-assistant h-full">
    <!-- 复制成功提示 -->
    <div 
      v-if="showCopyNotification" 
      class="fixed bottom-4 right-4 bg-gray-800 text-white px-4 py-2 rounded-md shadow-lg z-50 transition-opacity"
    >
      已复制到剪贴板
    </div>
    
    <!-- 对话列表侧边栏 -->
    <div v-if="!minimal && showConversations" class="fixed inset-0 bg-black bg-opacity-50 flex z-40" @click="showConversations = false">
      <div class="bg-white w-80 h-full overflow-y-auto p-4" @click.stop>
        <div class="flex justify-between items-center mb-4">
          <h3 class="text-lg font-semibold">对话历史</h3>
          <button @click="showConversations = false" class="text-gray-500 hover:text-gray-700">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        
        <div v-if="loadingConversations" class="flex justify-center py-10">
          <div class="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-blue-500"></div>
        </div>
        
        <div v-else-if="conversations.length === 0" class="text-center py-10 text-gray-500">
          没有历史对话
        </div>
        
        <div v-else class="space-y-2">
          <div 
            v-for="conv in conversations" 
            :key="conv.conversation_id" 
            @click="loadConversation(conv.conversation_id)"
            class="p-3 border rounded-md cursor-pointer hover:bg-gray-50"
            :class="{'bg-blue-50 border-blue-300': conv.conversation_id === conversationId}"
          >
            <div class="font-medium">{{ conv.title }}</div>
            <div class="flex justify-between text-xs text-gray-500 mt-1">
              <span>{{ formatDate(conv.last_time) }}</span>
              <span>{{ conv.message_count }}条消息</span>
            </div>
          </div>
        </div>
        
        <div class="mt-4 pt-4 border-t">
          <button 
            @click="startNewConversation" 
            class="w-full py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            新建对话
          </button>
        </div>
      </div>
    </div>
    
    <div class="flex h-full flex-col overflow-hidden rounded-lg border border-gray-200 bg-white shadow-md">
      <!-- 聊天页面头部 -->
      <div
        :class="['border-b', minimal ? 'px-4 py-2' : 'px-6 py-4', 'cursor-pointer']"
        @click.stop="emit('collapseRequest')"
      >
        <div class="flex justify-between items-center mb-2">
          <div class="flex items-center">
            <button 
              v-if="!minimal"
              @click="showConversations = true" 
              class="mr-3 text-gray-500 hover:text-gray-700"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h7" />
              </svg>
            </button>
            <h3 class="text-lg font-semibold whitespace-nowrap flex items-center space-x-1">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-blue-500" fill="currentColor" viewBox="0 0 24 24">
                <path d="M2 5a2 2 0 012-2h16a2 2 0 012 2v9a2 2 0 01-2 2H8l-6 6V5z" />
              </svg>
              <span>智能助手</span>
            </h3>
          </div>
          <div v-if="!minimal" class="flex items-center">
            <span class="inline-block w-2 h-2 rounded-full mr-2" 
                  :class="statusIndicatorClass"></span>
            <span class="text-sm text-gray-500">{{ statusText }}</span>
          </div>
        </div>
        
        <!-- 模式选择和课程选择 -->
        <div v-if="!minimal" class="flex flex-wrap items-center gap-4">
          <!-- 模式选择 -->
          <div class="flex items-center">
            <label class="text-sm text-gray-600 mr-2 whitespace-nowrap">模式:</label>
            <select 
              v-model="chatMode" 
              class="px-3 py-1.5 border rounded-md text-sm bg-white min-w-[120px]"
              @change="onModeChange"
            >
              <option value="general">普通AI问答</option>
              <option value="rag">知识库增强</option>
            </select>
          </div>
          
          <!-- 课程选择 - 仅在RAG模式下显示 -->
          <div v-if="chatMode === 'rag'" class="flex items-center">
            <label class="text-sm text-gray-600 mr-2 whitespace-nowrap">选择课程:</label>
            <select 
              v-model="selectedCourseId" 
              class="px-3 py-1.5 border rounded-md text-sm bg-white min-w-[200px]"
            >
              <option value="">请选择课程</option>
              <option v-for="course in courses" :key="course.id" :value="course.id">
                {{ course.name }} (ID: {{ course.id }})
              </option>
            </select>
            <!-- 调试信息 -->
            <div v-if="courses.length === 0 && !loadingCourses" class="ml-2 text-xs text-red-500">
              无可用课程
            </div>
            <div v-if="courses.length > 0" class="ml-2 text-xs text-green-500">
              {{ courses.length }}个课程可用
            </div>
            <div v-if="loadingCourses" class="ml-2 text-xs text-blue-500">
              加载中...
            </div>
            <!-- 当前选择显示 -->
            <div v-if="selectedCourseId" class="ml-2 text-xs text-gray-600">
              已选择: {{ selectedCourseId }}
            </div>
          </div>
          
          <!-- 加载状态 -->
          <div v-if="loadingCourses" class="flex items-center text-sm text-gray-500">
            <div class="animate-spin rounded-full h-4 w-4 border-t-2 border-b-2 border-blue-500 mr-2"></div>
            加载课程中...
          </div>
        </div>

        <div
          v-if="chatMode === 'rag' && selectedKnowledgeItems.length > 0"
          class="mt-3 flex flex-wrap items-center gap-2 rounded-md bg-indigo-50 px-3 py-2 text-sm text-indigo-700"
        >
          <span class="font-medium">当前文件：</span>
          <span class="rounded-full bg-white px-2.5 py-1 text-indigo-700 border border-indigo-100">
            {{ scopedKnowledgeFileLabel }}
          </span>
          <span class="text-indigo-500">仅检索该知识库文件</span>
          <button
            type="button"
            class="ml-auto rounded-md px-2 py-1 text-xs text-indigo-600 hover:bg-indigo-100"
            @click.stop="clearKnowledgeScope"
          >
            清除限定
          </button>
        </div>
      </div>
      
      <div :class="[minimal ? 'h-[calc(100vh-240px)]' : 'h-[calc(100vh-300px)]', 'p-4 overflow-y-auto']" ref="chatContainer">
        <div class="space-y-4">
          <!-- 系统消息 -->
          <div v-if="chatMessages.length === 0" class="flex items-start">
            <div class="flex-shrink-0 h-8 w-8 rounded-full flex items-center justify-center overflow-hidden mt-1">
              <img src="@/assets/images/atom.png" alt="AI" class="h-full w-full object-cover" />
            </div>
            <div class="ml-3 pl-2 max-w-[80%]">
              <p class="text-gray-800 font-medium">你好！我是易度新星 EduNova 智能学习助手。有什么可以帮助你的吗？</p>
            </div>
          </div>
          
          <!-- 用户消息和系统回复 -->
          <div v-for="(message, index) in chatMessages" :key="index">
            <!-- 用户消息 -->
            <div v-if="message.role === 'user'" class="flex items-start justify-end">
              <div class="mr-3 bg-blue-500 text-white rounded-lg py-2 px-4 max-w-[80%]">
                <p>{{ message.content }}</p>
              </div>
              <div class="flex-shrink-0 h-8 w-8 rounded-full bg-gray-300 overflow-hidden flex items-center justify-center">
                <template v-if="userAvatarUrl">
                  <img :src="formatAvatarUrl(userAvatarUrl)" alt="User" class="h-full w-full object-cover" />
                </template>
                <template v-else>
                  <span class="text-white font-medium">{{ userInitial }}</span>
                </template>
              </div>
            </div>
            
            <!-- 系统回复 -->
            <div v-else class="flex items-start mt-4">
              <div class="flex-shrink-0 h-8 w-8 rounded-full flex items-center justify-center overflow-hidden mt-1">
                <img src="@/assets/images/atom.png" alt="AI" class="h-full w-full object-cover" />
              </div>
              <div class="ml-3 pl-2 max-w-[80%] relative group">
                <!-- 使用v-if/v-else来区分是否有内容 -->
                <div v-if="message.content" class="text-gray-800 font-medium rounded-lg py-3 px-4">
                  <div
                    class="assistant-markdown"
                    v-html="renderAssistantMessage(message.content)"
                  ></div>
                  
                  <!-- 如果有引用来源 -->
                  <div v-if="message.sources && message.sources.length > 0" class="mt-3 pt-2 border-t border-gray-200">
                    <p class="text-xs font-bold text-gray-700">参考来源:</p>
                    <ul class="mt-1 space-y-1">
                      <li v-for="(source, sIdx) in message.sources" :key="sIdx" class="text-xs flex items-center">
                        <span class="mr-1 text-gray-500">•</span>
                        <a 
                          :href="formatFileUrl(source.url)" 
                          class="text-blue-600 hover:underline hover:text-blue-800" 
                          target="_blank"
                          :title="source.url"
                        >
                          {{ source.title || source.url }}
                        </a>
                      </li>
                    </ul>
                  </div>
                </div>
                
                <!-- 加载中指示器 - 当消息为空时显示 -->
                <div v-else class="flex items-center">
                  <span class="text-sm text-gray-500 mr-2">思考中</span>
                  <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                  <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0.2s"></div>
                  <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0.4s"></div>
                </div>
                
                <!-- 复制按钮 - 使用group-hover使其仅在悬停时显示 -->
                <button 
                  @click="copyMessageContent(message.content)"
                  class="absolute bottom-2 right-2 bg-gray-200 text-gray-600 p-1 rounded opacity-0 group-hover:opacity-100 transition-opacity"
                  title="复制内容"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <div class="px-4 py-3 border-t">
        <form @submit.prevent="sendMessage" class="flex items-center gap-2">
          <div class="relative flex-1">
            <input
              type="text"
              v-model="userInput"
              placeholder="输入你的问题..."
              class="w-full rounded-md border px-4 py-2 pr-12 focus:outline-none focus:ring-2 focus:ring-blue-500"
              :disabled="loading"
            />
            <button
              v-if="!isRecording"
              type="button"
              class="absolute right-2 top-1/2 -translate-y-1/2 rounded-full p-2 text-gray-500 transition hover:bg-gray-100 hover:text-blue-600 disabled:cursor-not-allowed disabled:opacity-50"
              :disabled="loading || isTranscribing"
              title="语音输入"
              aria-label="语音输入"
              @click="startRecording"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="22"/></svg>
            </button>
            <button
              v-else
              type="button"
              class="absolute right-2 top-1/2 -translate-y-1/2 rounded-full bg-red-50 p-2 text-red-500 transition hover:bg-red-100"
              title="停止录音"
              aria-label="停止录音"
              @click="stopRecording"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="10" height="10" x="7" y="7" rx="2"/></svg>
            </button>
          </div>
          <button
            type="submit"
            class="rounded-md bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
            :disabled="loading || isTranscribing || !userInput.trim() || (chatMode === 'rag' && !selectedCourseId)"
          >
            {{ loading ? '发送中...' : '发送' }}
          </button>
        </form>

        <div class="mt-2 flex min-h-[20px] items-center text-xs">
          <div v-if="isRecording" class="flex items-center text-red-500">
            <span class="mr-2 inline-block h-2 w-2 rounded-full bg-red-500"></span>
            录音中
          </div>
          <div v-else-if="isTranscribing" class="flex items-center text-blue-500">
            <span class="mr-2 h-3 w-3 animate-spin rounded-full border-2 border-blue-200 border-t-blue-500"></span>
            转写中
          </div>
        </div>
        
        <div class="flex flex-wrap gap-2 mt-3">
          <button 
            v-for="(suggestion, index) in currentSuggestions" 
            :key="index"
            @click="useSuggestion(suggestion)"
            class="text-xs bg-gray-100 hover:bg-gray-200 text-gray-800 px-2 py-1 rounded-md"
          >
            {{ suggestion }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, watch, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import axios from 'axios';
import DOMPurify from 'dompurify';
import { marked } from 'marked';
import katex from 'katex';
import 'katex/dist/katex.min.css';
import { courseAPI, ragAiAPI } from '../../api';
import { API_BASE_URL, API_ORIGIN } from '@/config/api';
import { useAudioTranscription } from '@/composables/useAudioTranscription';

// 定义接口
interface ChatMessage {
  role: string;
  content: string;
  sources?: Source[];
  timestamp?: number;
}

interface Source {
  title: string;
  url: string;
}

interface Conversation {
  conversation_id: string;
  title: string;
  start_time: number;
  last_time: number;
  message_count: number;
}

type SourceUsage = 'content' | 'format' | 'case' | 'image_asset';

interface ScopedKnowledgeItem {
  id?: number;
  course_id?: number | null;
  file_path: string;
  purpose?: string;
  usage: SourceUsage;
  knowledgePoint: string;
  isRequired: boolean;
  file_name: string;
}

const renderedAssistantMessageCache = new Map<string, string>();
const route = useRoute();
const router = useRouter();

marked.setOptions({
  gfm: true,
  breaks: true
});

const props = defineProps({
  courseId: {
    type: [Number, String],
    default: null
  },
  // 当 minimal 为 true 时：
  // 1) 默认启用 RAG 并锁定到传入的 courseId
  // 2) 隐藏对话历史、模式/课程选择等额外 UI
  minimal: {
    type: Boolean,
    default: false
  }
});

const chatContainer = ref<HTMLElement | null>(null);
const userInput = ref('');
const loading = ref(false);
const chatMessages = ref<ChatMessage[]>([]);
const conversationId = ref('');
const userAvatarUrl = ref('');
const userInitial = ref('');
const showCopyNotification = ref(false);
const {
  isRecording,
  isTranscribing,
  startRecording,
  stopRecording,
} = useAudioTranscription({
  filePrefix: 'assistant_message',
  onTranscribed: (text) => {
    userInput.value = userInput.value ? `${userInput.value} ${text}`.trim() : text;
  },
  onError: (message, error) => {
    console.error(message, error);
    alert(message);
  }
});

// 对话历史相关
const showConversations = ref(false);
const loadingConversations = ref(false);
const conversations = ref<Conversation[]>([]);

// 课程相关
const courses = ref<any[]>([]);
const selectedCourseId = ref<string | number>('');
const useRag = ref<boolean>(true);
const loadingCourses = ref<boolean>(false);
const selectedKnowledgeItems = ref<ScopedKnowledgeItem[]>([]);
const autoLaunchSignature = ref('');

// 新增：聊天模式相关
const chatMode = ref<'general' | 'rag'>('general');

// 提问建议
const suggestions = [
  '什么是机器学习？',
  '如何提高学习效率？',
  '推荐一些学习资源',
  '这门课程的难点是什么？',
  '如何准备考试？'
];

// RAG模式专用建议
const ragSuggestions = [
  '这门课程的主要内容是什么？',
  '课程中的重点概念有哪些？',
  '如何理解课程中的难点？',
  '课程相关的实践项目有哪些？',
  '这门课程与其他课程有什么联系？'
];

// 计算当前应该显示的建议
const currentSuggestions = computed(() => {
  return chatMode.value === 'rag' ? ragSuggestions : suggestions;
});

// 状态指示器
const statusIndicatorClass = computed(() => {
  if (chatMode.value === 'rag' && !selectedCourseId.value) {
    return 'bg-yellow-500'; // 黄色：需要选择课程
  }
  return 'bg-green-500'; // 绿色：就绪
});

const statusText = computed(() => {
  if (chatMode.value === 'rag' && !selectedCourseId.value) {
    return '请选择课程';
  }
  if (chatMode.value === 'rag' && selectedCourseId.value) {
    return '知识库模式（如无知识库将使用普通模式）';
  }
  return '普通模式';
});

const scopedKnowledgeFileLabel = computed(() => {
  if (selectedKnowledgeItems.value.length === 0) {
    return '';
  }
  return selectedKnowledgeItems.value
    .map(item => item.file_name || item.file_path.split('/').pop() || item.file_path)
    .join('、');
});

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function extractMathExpressions(content: string): { markdown: string; replacements: Map<string, string> } {
  const pattern = /(\$\$[\s\S]+?\$\$|\\\[[\s\S]+?\\\]|\\\([\s\S]+?\\\)|(?<!\\)\$[^$\n]+?(?<!\\)\$)/g;
  const replacements = new Map<string, string>();
  let index = 0;

  const markdown = content.replace(pattern, (token) => {
    const isDisplayMode = token.startsWith('$$') || token.startsWith('\\[');
    const expression = token.startsWith('$$')
      ? token.slice(2, -2)
      : token.startsWith('\\[')
        ? token.slice(2, -2)
        : token.startsWith('\\(')
          ? token.slice(2, -2)
          : token.slice(1, -1);

    const placeholder = `KATEX_PLACEHOLDER_${index++}`;
    try {
      replacements.set(
        placeholder,
        katex.renderToString(expression.trim(), {
          displayMode: isDisplayMode,
          throwOnError: false,
          strict: 'ignore'
        })
      );
    } catch {
      replacements.set(placeholder, escapeHtml(token));
    }

    return placeholder;
  });

  return { markdown, replacements };
}

function renderAssistantMessage(content: string): string {
  if (!content) {
    return '';
  }
  const cached = renderedAssistantMessageCache.get(content);
  if (cached) {
    return cached;
  }

  const { markdown, replacements } = extractMathExpressions(content);
  let parsedHtml = '';
  try {
    parsedHtml = String(marked.parse(markdown));
  } catch (error) {
    console.error('Markdown 渲染失败:', error);
    parsedHtml = `<p>${content.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</p>`;
  }

  let renderedHtml = DOMPurify.sanitize(parsedHtml, {
    USE_PROFILES: { html: true }
  });

  replacements.forEach((html, placeholder) => {
    renderedHtml = renderedHtml.replaceAll(placeholder, html);
  });

  if (renderedAssistantMessageCache.size > 200) {
    renderedAssistantMessageCache.clear();
  }
  renderedAssistantMessageCache.set(content, renderedHtml);
  return renderedHtml;
}

function formatAssistantErrorMessage(rawMessage: unknown): string {
  const message = String(rawMessage || '').trim();
  if (!message) {
    return '抱歉，智能助手暂时不可用，请稍后再试。';
  }

  if (/AllocationQuota\.FreeTierOnly|free tier/i.test(message)) {
    return '当前 AI 服务的免费额度已用尽。请在服务端模型平台关闭“仅使用免费额度”限制，或更换可用的付费 API Key 后再试。';
  }

  return `抱歉，智能助手暂时不可用：${message}`;
}

// 复制消息内容
function copyMessageContent(content: string): void {
  if (!content) return;
  
  navigator.clipboard.writeText(content)
    .then(() => {
      // 显示复制成功提示
      showCopyNotification.value = true;
      setTimeout(() => {
        showCopyNotification.value = false;
      }, 2000);
    })
    .catch(err => {
      console.error('复制失败:', err);
    });
}

// 格式化头像URL
function formatAvatarUrl(url: string): string {
  if (!url) return '';
  
  // 如果已经是完整URL，直接返回
  if (url.startsWith('http')) {
    return url;
  }
  
  // 如果是相对路径，添加基础URL
  return `${API_ORIGIN}${url}`;
}

// 格式化文件URL
function formatFileUrl(url: string): string {
  if (!url) return '';
  
  // 如果已经是完整URL，直接返回
  if (url.startsWith('http')) {
    return url;
  }
  
  // 如果是相对路径，根据课程ID构建URL
  if (props.courseId) {
    return `${API_ORIGIN}/uploads/materials/${props.courseId}/${encodeURIComponent(url)}`;
  }
  
  // 如果没有课程ID，尝试构建一个基本URL
  return `${API_ORIGIN}/uploads/${encodeURIComponent(url)}`;
}

const emit = defineEmits(['collapseRequest', 'conversation-updated']);

function getQueryValue(value: unknown): string {
  return typeof value === 'string' ? value.trim() : '';
}

function normalizeSourceUsageValue(value: unknown): SourceUsage {
  const normalized = String(value || '').trim().toLowerCase();
  if (normalized === 'format' || normalized === 'case' || normalized === 'image_asset') {
    return normalized;
  }
  return 'content';
}

function buildScopedKnowledgeItemsFromRoute(): ScopedKnowledgeItem[] {
  const filePath = getQueryValue(route.query.ragFilePath);
  if (!filePath) {
    return [];
  }

  const rawCourseId = getQueryValue(route.query.courseId);
  const parsedCourseId = rawCourseId ? Number(rawCourseId) : NaN;
  const rawKnowledgeId = getQueryValue(route.query.ragKnowledgeId);
  const parsedKnowledgeId = rawKnowledgeId ? Number(rawKnowledgeId) : NaN;
  const fileName = getQueryValue(route.query.ragFileName) || filePath.split('/').pop() || filePath;

  return [{
    id: Number.isFinite(parsedKnowledgeId) ? parsedKnowledgeId : undefined,
    course_id: Number.isFinite(parsedCourseId) ? parsedCourseId : null,
    file_path: filePath,
    purpose: getQueryValue(route.query.ragPurpose) || 'general',
    usage: normalizeSourceUsageValue(route.query.ragUsage),
    knowledgePoint: getQueryValue(route.query.ragKnowledgePoint) || '文件内容检索',
    isRequired: true,
    file_name: fileName
  }];
}

function syncAssistantContextFromRoute() {
  selectedKnowledgeItems.value = buildScopedKnowledgeItemsFromRoute();

  const routeCourseId = getQueryValue(route.query.courseId);
  const fallbackCourseId = props.courseId !== null && props.courseId !== undefined ? String(props.courseId) : '';
  const nextCourseId = routeCourseId || fallbackCourseId;

  if (selectedKnowledgeItems.value.length > 0 || nextCourseId) {
    chatMode.value = 'rag';
  } else if (!props.minimal) {
    chatMode.value = 'general';
  }

  if (nextCourseId) {
    selectedCourseId.value = nextCourseId;
  } else if (selectedKnowledgeItems.value.length === 0 && !props.minimal) {
    selectedCourseId.value = '';
  }
}

function buildSelectedKnowledgeItemsPayload() {
  return selectedKnowledgeItems.value.map(item => ({
    id: item.id,
    course_id: item.course_id ?? null,
    file_path: item.file_path,
    purpose: item.purpose || 'general',
    usage: item.usage,
    knowledgePoint: item.knowledgePoint,
    isRequired: item.isRequired
  }));
}

async function maybeAutoLaunchFromRoute() {
  const shouldAutoStart = getQueryValue(route.query.ragAutostart) === '1';
  const prompt = getQueryValue(route.query.ragPrompt);
  const signature = [
    getQueryValue(route.query.courseId),
    getQueryValue(route.query.ragFilePath),
    prompt
  ].join('|');

  if (!shouldAutoStart || !prompt || !signature) {
    return;
  }
  if (autoLaunchSignature.value === signature || loading.value) {
    return;
  }
  if (chatMode.value !== 'rag' || (!selectedCourseId.value && selectedKnowledgeItems.value.length === 0)) {
    return;
  }

  autoLaunchSignature.value = signature;
  startNewConversation();
  updateWelcomeMessage();
  userInput.value = prompt;
  await nextTick();
  await sendMessage();

  const nextQuery = { ...route.query };
  delete nextQuery.ragAutostart;
  await router.replace({ query: nextQuery });
}

async function clearKnowledgeScope() {
  selectedKnowledgeItems.value = [];
  const nextQuery = { ...route.query };
  delete nextQuery.ragMode;
  delete nextQuery.ragAutostart;
  delete nextQuery.ragFilePath;
  delete nextQuery.ragFileName;
  delete nextQuery.ragPurpose;
  delete nextQuery.ragPrompt;
  delete nextQuery.ragKnowledgeId;
  delete nextQuery.ragKnowledgePoint;
  delete nextQuery.ragUsage;
  await router.replace({ query: nextQuery });
}

onMounted(async () => {
  // 获取用户信息
  try {
    // 使用当前用户的个人资料API而不是按ID获取
    const userResponse = await axios.get(`${API_BASE_URL}/auth/profile`, {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      }
    });
    
    if (userResponse.data && userResponse.data.user) {
      const userData = userResponse.data.user;
      console.log('获取到用户信息:', userData);
      
      // 设置用户头像URL
      if (userData.avatar_url) {
        userAvatarUrl.value = userData.avatar_url;
        console.log('设置用户头像URL:', userAvatarUrl.value);
      } else {
        // 如果没有头像，使用用户名的首字母
        userInitial.value = userData.username ? userData.username.charAt(0).toUpperCase() : 'U';
        console.log('设置用户初始字母:', userInitial.value);
      }
    } else {
      // 如果无法获取用户信息，使用默认首字母
      setDefaultUserInitial();
    }
  } catch (error) {
    console.error('无法获取用户信息:', error);
    setDefaultUserInitial();
  }

  // 检查AI模块状态
  try {
    const statusResponse = await ragAiAPI.getStatus();
    console.log('AI模块状态:', statusResponse);
    
    // 由于响应拦截器已经返回response.data，所以这里直接使用response
    const responseData = statusResponse as any;
    if (responseData && !responseData.ai_enabled) {
      chatMessages.value.push({
        role: 'assistant',
        content: '注意：智能助手功能目前不可用。请确保已配置API密钥。'
      });
    }
  } catch (error) {
    console.error('无法获取AI模块状态:', error);
    chatMessages.value.push({
      role: 'assistant',
      content: '注意：智能助手功能目前可能不可用。请稍后再试。'
    });
  }
  
  // 获取对话列表
  await fetchConversations();
  
  // 获取课程列表
  await fetchCourses();

  syncAssistantContextFromRoute();

  if (props.minimal) {
    chatMode.value = 'rag';
    if (props.courseId) {
      selectedCourseId.value = props.courseId;
    }
  }
  
  // 只有在没有消息时才设置欢迎消息
  if (chatMessages.value.length === 0) {
    updateWelcomeMessage();
  }

  await maybeAutoLaunchFromRoute();
  
  // 滚动到底部
  scrollToBottom();
});

watch(chatMessages, () => {
  // 消息更新后滚动到底部
  nextTick(() => {
    scrollToBottom();
  });
});

// 监听课程选择变化
watch(selectedCourseId, (newCourseId) => {
  console.log('课程选择变化:', newCourseId);
  if (chatMode.value === 'rag' && newCourseId) {
    // 当在RAG模式下选择课程时，更新欢迎消息
    updateWelcomeMessage();
  }
});

// 监听课程数据变化
watch(courses, (newCourses) => {
  console.log('课程数据更新:', newCourses);
  // 如果当前选中的课程不在课程列表中，清空选择
  if (selectedCourseId.value && !newCourses.find(c => c.id == selectedCourseId.value)) {
    selectedCourseId.value = '';
  }
});

watch(
  () => [
    route.query.courseId,
    route.query.ragAutostart,
    route.query.ragFilePath,
    route.query.ragFileName,
    route.query.ragPurpose,
    route.query.ragPrompt,
    route.query.ragKnowledgeId,
    route.query.ragKnowledgePoint,
    route.query.ragUsage
  ],
  async () => {
    syncAssistantContextFromRoute();
    await maybeAutoLaunchFromRoute();
  }
);

function scrollToBottom() {
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight;
  }
}

async function sendMessage() {
  if (!userInput.value.trim() || loading.value) return;
  
  // 在RAG模式下检查是否选择了课程
  if (chatMode.value === 'rag' && !selectedCourseId.value) {
    alert('请先选择课程以启用知识库增强功能');
    return;
  }
  
  const message = userInput.value;
  userInput.value = '';
  
  // 添加用户消息到聊天记录
  chatMessages.value.push({
    role: 'user',
    content: message,
    timestamp: Date.now()
  });
  
  // 添加一个空的系统回复作为占位符
  chatMessages.value.push({
    role: 'assistant',
    content: '',
    timestamp: Date.now()
  });
  
  // 滚动到底部
  await nextTick();
  scrollToBottom();
  
  loading.value = true;
  
  try {
    // 构建请求参数
    const params: any = {
      message,
      stream: true
    };
    
    // 根据模式设置参数
    if (chatMode.value === 'rag' && selectedCourseId.value) {
      params.course_id = selectedCourseId.value;
      params.use_rag = true; // 尝试使用RAG，如果失败会自动回退到普通模式
      if (selectedKnowledgeItems.value.length > 0) {
        params.selectedKnowledgeItems = buildSelectedKnowledgeItemsPayload();
      }
    } else {
      params.use_rag = false;
    }
    
    // 如果有对话ID，添加到参数中
    if (conversationId.value) {
      params.conversation_id = conversationId.value;
    }
    
    console.log('发送聊天请求:', params);
    
    const response = await fetch(`${API_BASE_URL}/rag/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      },
      body: JSON.stringify(params)
    });
    
    if (!response.ok) {
      let errorMessage = `HTTP error! status: ${response.status}`;
      try {
        const errorPayload = await response.json();
        if (errorPayload && typeof errorPayload === 'object') {
          errorMessage = String((errorPayload as any).message || (errorPayload as any).msg || errorMessage);
        }
      } catch {
        try {
          const errorText = await response.text();
          if (errorText.trim()) {
            errorMessage = errorText.trim();
          }
        } catch {
          // ignore secondary parsing failure
        }
      }
      throw new Error(errorMessage);
    }
    
    // 获取响应的reader
    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('无法获取响应流');
    }
    
    // 处理流式响应
    const decoder = new TextDecoder();
    let buffer = '';
    let lastRenderTime = Date.now();
    const renderInterval = 500; // 每500毫秒渲染一次
    
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      // 解码二进制数据
      buffer += decoder.decode(value, { stream: true });
      
      // 处理接收到的数据行
      const lines = buffer.split('\n\n');
      buffer = lines.pop() || '';
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.substring(6));
            
            // 处理内容更新
            if (data.content) {
              // 如果是第一个内容块且消息当前为空，去除开头的空白
              if (!chatMessages.value[chatMessages.value.length - 1].content) {
                chatMessages.value[chatMessages.value.length - 1].content = data.content.trimStart();
              } else {
                chatMessages.value[chatMessages.value.length - 1].content += data.content;
              }
              
              // 实时渲染Markdown：每隔一定时间或内容达到一定长度时渲染
              const now = Date.now();
              if (now - lastRenderTime > renderInterval) {
                // 强制Vue更新视图
                chatMessages.value = [...chatMessages.value];
                lastRenderTime = now;
                
                // 滚动到底部
                nextTick(() => {
                  scrollToBottom();
                });
              }
            }

            if (data.status === 'error') {
              chatMessages.value[chatMessages.value.length - 1].content =
                formatAssistantErrorMessage(data.message);
              chatMessages.value = [...chatMessages.value];
              loading.value = false;
              return;
            }
            
            // 处理完成信号
              if (data.status === 'done') {
                // 保存对话ID
                if (data.conversation_id) {
                  conversationId.value = data.conversation_id;
                  emit('conversation-updated', data.conversation_id);
                }
              
              // 添加引用来源
              if (data.sources && Array.isArray(data.sources) && data.sources.length > 0) {
                console.log("收到引用来源:", data.sources);
                chatMessages.value[chatMessages.value.length - 1].sources = data.sources;
                
                // 检查AI回复是否已经包含"参考来源:"，如果没有则添加
                const currentMessage = chatMessages.value[chatMessages.value.length - 1].content;
                if (!currentMessage.includes("参考来源:") && !currentMessage.includes("参考来源：")) {
                  // 添加一个空行和参考来源标记
                  chatMessages.value[chatMessages.value.length - 1].content += "\n\n参考来源: 见下方链接";
                }
              } else {
                console.log("没有收到引用来源");
              }
              
              // 最后一次渲染，确保所有内容都已渲染
              chatMessages.value = [...chatMessages.value];
              
              loading.value = false;
              return;
            }
          } catch (error) {
            console.error('解析流式响应失败:', error);
          }
        }
      }
    }
    
    loading.value = false;
  } catch (error) {
    console.error('发送消息失败:', error);
    const friendlyMessage = formatAssistantErrorMessage(
      error instanceof Error ? error.message : String(error)
    );
    
    // 如果已经添加了AI消息，更新为错误消息
    if (chatMessages.value.length > 1) {
      chatMessages.value[chatMessages.value.length - 1].content = friendlyMessage;
    } else {
      // 如果没有添加AI消息，添加一个错误消息
      chatMessages.value.push({
        role: 'assistant',
        content: friendlyMessage
      });
    }
    
    loading.value = false;
  }
}

function useSuggestion(suggestion: string): void {
  userInput.value = suggestion;
}

// 格式化日期
function formatDate(timestamp: number): string {
  if (!timestamp) return '';
  const date = new Date(timestamp * 1000);
  return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

// 获取对话列表
async function fetchConversations() {
  loadingConversations.value = true;
  
  try {
    const response = await ragAiAPI.getConversations(props.courseId);
    
    // 由于响应拦截器已经返回response.data，所以这里直接使用response
    const responseData = response as any;
    if (responseData && responseData.status === 'success') {
      conversations.value = responseData.conversations || [];
    } else {
      throw new Error(responseData?.message || '未知错误');
    }
  } catch (error) {
    console.error('获取对话列表失败:', error);
    conversations.value = [];
  } finally {
    loadingConversations.value = false;
  }
}

// 加载指定对话
async function loadConversation(convId: string): Promise<void> {
  if (convId === conversationId.value) {
    showConversations.value = false;
    return;
  }
  
  try {
    const response = await ragAiAPI.getChatHistory(convId);
    
    // 由于响应拦截器已经返回response.data，所以这里直接使用response
    const responseData = response as any;
    if (responseData && responseData.status === 'success') {
      chatMessages.value = responseData.history.map((msg: any) => ({
        role: msg.role,
        content: msg.content,
        timestamp: msg.timestamp
      }));
      conversationId.value = convId;
      emit('conversation-updated', convId);
      showConversations.value = false;
    } else {
      throw new Error(responseData?.message || '未知错误');
    }
  } catch (error) {
    console.error('加载对话历史失败:', error);
    chatMessages.value.push({
      role: 'assistant',
      content: '加载对话历史失败，请稍后再试。'
    });
  }
}

// 开始新对话
function startNewConversation() {
  conversationId.value = '';
  emit('conversation-updated', '');
  chatMessages.value = [];
  showConversations.value = false;
}

function setDefaultUserInitial() {
  // 尝试从localStorage获取用户信息
  try {
    const userDataStr = localStorage.getItem('user');
    if (userDataStr) {
      const userData = JSON.parse(userDataStr);
      if (userData && userData.username) {
        userInitial.value = userData.username.charAt(0).toUpperCase();
        return;
      }
    }
  } catch (e) {
    console.error('解析localStorage中的用户信息失败:', e);
  }
  
  // 如果无法从localStorage获取，使用默认值
  userInitial.value = 'U';
}

// 获取课程列表
async function fetchCourses() {
  loadingCourses.value = true;
  try {
    const response = await courseAPI.getCourses();
    console.log('课程API响应:', response);
    
    // 检查响应格式并正确提取课程数据
    if (response && typeof response === 'object' && 'courses' in response) {
      courses.value = (response as any).courses || [];
    } else if (Array.isArray(response)) {
      courses.value = response;
    } else {
      console.warn('课程API响应格式异常:', response);
      courses.value = [];
    }
    
    console.log('获取到课程列表:', courses.value);
    
    // 如果传入了课程ID但课程不在列表中，添加一个占位符
    if (props.courseId && !courses.value.find(c => c.id == props.courseId)) {
      courses.value.push({
        id: props.courseId,
        name: `课程 #${props.courseId}`,
        description: '课程信息加载中...'
      });
    }
  } catch (error) {
    console.error('获取课程列表失败:', error);
    courses.value = [];
    
    // 如果传入了课程ID，至少添加一个占位符
    if (props.courseId) {
      courses.value.push({
        id: props.courseId,
        name: `课程 #${props.courseId}`,
        description: '课程信息加载失败'
      });
    }
  } finally {
    loadingCourses.value = false;
  }
}

function onModeChange() {
  // 模式切换时的逻辑
  if (chatMode.value === 'general') {
    // 切换到普通模式时，清空课程选择
    selectedCourseId.value = '';
  } else if (chatMode.value === 'rag') {
    // 切换到RAG模式时，如果有传入的课程ID，自动选择
    if (props.courseId) {
      selectedCourseId.value = props.courseId;
    }
  }
  
  // 只有在有对话ID的情况下才清空对话，表示这是一个新的对话
  if (conversationId.value) {
    conversationId.value = '';
    chatMessages.value = [];
    
    // 更新欢迎消息
    updateWelcomeMessage();
  }
}

function updateWelcomeMessage() {
  // Only update welcome message if there are no existing messages
  if (chatMessages.value.length > 0) return;
  
  let welcomeMessage = '';
  if (chatMode.value === 'general') {
    welcomeMessage = '你好！我是易度新星 EduNova 智能学习助手。有什么可以帮助你的吗？';
  } else {
    if (selectedCourseId.value) {
      const course = courses.value.find(c => c.id == selectedCourseId.value);
      const courseName = course ? course.name : `课程 #${selectedCourseId.value}`;
      if (selectedKnowledgeItems.value.length > 0) {
        welcomeMessage = `你好！我是易度新星 EduNova 智能学习助手。我已连接到"${courseName}"中的知识库文件《${scopedKnowledgeFileLabel.value}》。接下来我会只围绕这份资料进行检索和回答。`;
      } else {
        welcomeMessage = `你好！我是易度新星 EduNova 智能学习助手。我已连接到"${courseName}"。我将基于课程的知识库回答，请随时提问！`;
      }
    } else {
      welcomeMessage = '你好！我是易度新星 EduNova 智能学习助手。请选择课程以启用知识库增强功能。';
    }
  }
  
  chatMessages.value.push({
    role: 'assistant',
    content: welcomeMessage
  });
}
</script>

<style>
.assistant-markdown {
  color: #1f2937;
  font-weight: 500;
  line-height: 1.75;
  word-break: break-word;
  background: transparent;
}

.assistant-markdown > :first-child {
  margin-top: 0;
}

.assistant-markdown > :last-child {
  margin-bottom: 0;
}

.assistant-markdown :is(h1, h2, h3, h4, h5, h6) {
  margin: 1rem 0 0.65rem;
  font-weight: 700;
  line-height: 1.4;
  color: #111827;
}

.assistant-markdown h1 {
  font-size: 1.35rem;
}

.assistant-markdown h2 {
  font-size: 1.2rem;
}

.assistant-markdown h3 {
  font-size: 1.08rem;
}

.assistant-markdown p,
.assistant-markdown ul,
.assistant-markdown ol,
.assistant-markdown blockquote,
.assistant-markdown table,
.assistant-markdown pre {
  margin: 0.7rem 0;
}

.assistant-markdown ul,
.assistant-markdown ol {
  padding-left: 1.4rem;
}

.assistant-markdown li + li {
  margin-top: 0.2rem;
}

.assistant-markdown blockquote {
  padding-left: 0.9rem;
  border-left: 3px solid #cbd5e1;
  color: #475569;
}

.assistant-markdown code {
  padding: 0.15rem 0.35rem;
  border-radius: 0.35rem;
  background: #e5e7eb;
  font-family: Consolas, 'Courier New', monospace;
  font-size: 0.92em;
}

.assistant-markdown pre {
  overflow-x: auto;
  padding: 0.9rem 1rem;
  border-radius: 0.85rem;
  background: #0f172a;
  color: #e2e8f0;
}

.assistant-markdown pre code {
  padding: 0;
  background: transparent;
  color: inherit;
}

.assistant-markdown table {
  display: block;
  overflow-x: auto;
  width: 100%;
  border-collapse: collapse;
}

.assistant-markdown th,
.assistant-markdown td {
  padding: 0.55rem 0.75rem;
  border: 1px solid #d1d5db;
  text-align: left;
  vertical-align: top;
}

.assistant-markdown th {
  background: #f3f4f6;
  font-weight: 700;
}

.assistant-markdown hr {
  margin: 1rem 0;
  border: 0;
  border-top: 1px solid #d1d5db;
}

.assistant-markdown a {
  color: #2563eb;
  text-decoration: underline;
}

.assistant-markdown .katex-display {
  overflow-x: auto;
  overflow-y: hidden;
  padding: 0.25rem 0;
}

.assistant-markdown .katex {
  font-size: 1.04em;
}
</style> 
