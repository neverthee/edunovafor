<template>
  <div class="material-preview-container">
    <!-- 左侧文件列表 -->
    <div
      v-if="!props.hideSidebar"
      :class="[
        'file-sidebar transition-all duration-200 relative',
        isSidebarCollapsed ? 'w-20 rounded-r-lg cursor-pointer' : 'w-72'
      ]"
      @click="isSidebarCollapsed && toggleSidebar"
    >
      <!-- 折叠状态下显示大图标 -->
      <template v-if="isSidebarCollapsed">
        <div
          class="flex flex-col items-center justify-center py-4 space-y-3 cursor-pointer"
          @click.stop="toggleSidebar"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-blue-500" fill="currentColor" viewBox="0 0 24 24">
            <path d="M3 4.5A1.5 1.5 0 014.5 3h6.379a1.5 1.5 0 011.06.44l1.621 1.62a1.5 1.5 0 001.06.44H19.5A1.5 1.5 0 0121 6v13.5A1.5 1.5 0 0119.5 21h-15A1.5 1.5 0 013 19.5v-15z" />
          </svg>
        </div>
      </template>

      <!-- 展开时内容 -->
      <template v-if="!isSidebarCollapsed">
        <div class="flex h-full flex-col">
          <div class="border-b border-gray-200 pb-4">
            <button
              v-if="!props.hideBackButton"
              @click.stop="closePreview"
              class="mb-4 inline-flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-gray-700 transition hover:bg-gray-50"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z" clip-rule="evenodd" />
              </svg>
              <span>返回上一页</span>
            </button>

            <h3
              class="text-lg font-semibold flex items-center space-x-1 whitespace-nowrap cursor-pointer"
              @click.stop="toggleSidebar"
            >
              <span>课程资源</span>
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-blue-500" fill="currentColor" viewBox="0 0 24 24">
                <path d="M3 4.5A1.5 1.5 0 014.5 3h6.379a1.5 1.5 0 011.06.44l1.621 1.62a1.5 1.5 0 001.06.44H19.5A1.5 1.5 0 0121 6v13.5A1.5 1.5 0 0119.5 21h-15A1.5 1.5 0 013 19.5v-15z" />
              </svg>
            </h3>
          </div>

          <div v-if="materials.length > 0" class="mt-4 flex-1 space-y-2 overflow-y-auto pr-1">
            <div 
              v-for="material in materials" 
              :key="material.id" 
              @click="selectMaterial(material)"
              class="file-item p-2 rounded-md cursor-pointer flex items-center"
              :class="{'bg-blue-100': selectedMaterial && selectedMaterial.id === material.id}"
            >
              <span class="mr-2" v-html="getMaterialIcon(material.material_type)"></span>
              <div class="truncate">
                <p class="font-medium truncate">{{ material.title }}</p>
                <p class="text-xs text-gray-500">{{ material.material_type }} · {{ material.size }}</p>
              </div>
            </div>
          </div>
          <div v-else class="flex flex-1 items-center justify-center text-center py-4">
            <p class="text-gray-500">暂无课件资源</p>
          </div>
        </div>
      </template>
    </div>

    <!-- 右侧预览区域 -->
    <div :class="['preview-area', { 'preview-area--solo': props.hideSidebar }]">
      <div v-if="selectedMaterial" class="preview-content">
        <div v-if="!props.hidePreviewHeader" class="preview-header">
          <h2 class="text-xl font-bold">{{ selectedMaterial.title }}</h2>
          <div class="text-sm text-gray-500 mb-4">
            {{ selectedMaterial.material_type }} · {{ selectedMaterial.size }}
          </div>
          <div class="flex space-x-3">
            <button @click="downloadMaterial(selectedMaterial.id)" class="text-blue-600 hover:text-blue-800">
              下载
            </button>
          </div>
        </div>
        
        <div class="preview-body">
          <!-- PDF 预览 -->
          <div v-if="isPdfFile(selectedMaterial)" class="pdf-preview h-full min-h-[900px]">
            <PdfViewer 
              :pdf-url="getFileUrl(selectedMaterial.file_path || '')" 
              :initial-page="resolvedInitialPage"
              @download="downloadMaterial(selectedMaterial.id)" 
            />
          </div>
          
          <!-- Markdown预览 -->
          <div v-else-if="isMarkdownFile(selectedMaterial)" class="markdown-preview">
            <MarkdownViewer 
              :url="getFileUrl(selectedMaterial.file_path || '')" 
            />
          </div>
          
          <!-- 图片预览 -->
          <div v-else-if="isImageFile(selectedMaterial)" class="image-preview min-h-[900px] flex items-center justify-center">
            <img :src="getFileUrl(selectedMaterial.file_path)" alt="图片预览" class="max-w-full max-h-[600px] mx-auto" />
          </div>
          
          <!-- 视频预览 -->
          <div v-else-if="isVideoFile(selectedMaterial)" class="video-preview min-h-[900px]">
            <video 
              :src="getFileUrl(selectedMaterial.file_path)" 
              controls 
              preload="metadata"
              controlsList="nodownload"
              class="w-full max-h-[600px]"
            ></video>
            <div class="mt-4 text-center">
              <p class="text-sm text-gray-500">如果视频加载缓慢或无法播放，请尝试下载后观看</p>
              <div class="flex justify-center space-x-4 mt-2">
                <a 
                  :href="getFileUrl(selectedMaterial.file_path)" 
                  target="_blank" 
                  class="px-4 py-2 bg-blue-600 text-white rounded-md"
                >
                  在新窗口打开
                </a>
                <button 
                  @click="downloadMaterial(selectedMaterial.id)" 
                  class="px-4 py-2 bg-gray-200 text-gray-800 rounded-md"
                >
                  下载视频
                </button>
              </div>
            </div>
          </div>
          
          <!-- 文本预览 -->
          <div v-else-if="isTextFile(selectedMaterial)" class="text-preview min-h-[900px]">
            <div v-if="textContent" class="p-4 border rounded-md bg-gray-50 whitespace-pre-wrap">
              {{ textContent }}
            </div>
            <div v-else class="flex justify-center items-center h-[400px]">
              <p class="text-gray-500">加载文本内容中...</p>
            </div>
          </div>
          
          <!-- Office 文档优先预览转换后的 PDF -->
          <div v-else-if="isOfficeDocument(selectedMaterial.material_type)" class="office-preview min-h-[900px]">
            <div v-if="hasGeneratedPdfPreview(selectedMaterial)" class="pdf-preview h-full min-h-[900px]">
              <PdfViewer
                :pdf-url="getOfficePreviewUrl(selectedMaterial)"
                :initial-page="resolvedInitialPage"
                @download="downloadMaterial(selectedMaterial.id)"
              />
            </div>
            <div v-else-if="supportsLightweightDocxPreview(selectedMaterial)" class="min-h-[900px]">
              <DocxViewer :url="getFileUrl(selectedMaterial.file_path || '')" />
            </div>
            <div v-else-if="supportsSpreadsheetPreview(selectedMaterial)" class="min-h-[900px]">
              <SpreadsheetViewer :url="getFileUrl(selectedMaterial.file_path || '')" />
            </div>
            <div v-else-if="supportsLightweightPptxPreview(selectedMaterial)" class="min-h-[900px]">
              <PptxViewer :url="getFileUrl(selectedMaterial.file_path || '')" />
            </div>
            <div v-else class="mt-4 flex min-h-[480px] flex-col items-center justify-center rounded-xl border border-dashed border-gray-300 bg-gray-50 p-8 text-center">
              <p class="text-base font-medium text-gray-700">{{ getOfficePreviewMessage(selectedMaterial) }}</p>
              <p v-if="selectedMaterial.preview_error" class="mt-2 max-w-2xl text-sm text-gray-500">
                {{ selectedMaterial.preview_error }}
              </p>
              <div class="mt-6 flex flex-wrap justify-center gap-3">
                <button
                  @click="downloadMaterial(selectedMaterial.id)"
                  class="rounded-md bg-blue-600 px-4 py-2 text-white"
                >
                  下载原文件
                </button>
                <a
                  :href="getFileUrl(selectedMaterial.file_path)"
                  target="_blank"
                  class="rounded-md bg-gray-200 px-4 py-2 text-gray-800"
                >
                  打开原文件
                </a>
              </div>
            </div>
            <div class="mt-4 flex flex-col gap-3 rounded-xl bg-gray-50 p-4 md:flex-row md:items-center md:justify-between">
              <div>
                <p class="text-base font-medium text-gray-700">Office 文件优先显示转换后的 PDF 预览</p>
                <p class="text-sm text-gray-500">
                  如果当前环境缺少 LibreOffice 等转换组件，docx、xlsx、pptx 会自动回退到浏览器轻量预览。
                </p>
              </div>
              <div class="flex flex-wrap gap-3">
                <button
                  @click="downloadMaterial(selectedMaterial.id)"
                  class="rounded-md bg-gray-200 px-4 py-2 text-gray-800"
                >
                  下载文件
                </button>
              </div>
            </div>
          </div>
          
          <!-- 不支持预览的文件类型 -->
          <div v-else class="unsupported-preview flex flex-col items-center justify-center min-h-[900px]">
            <div class="text-6xl text-gray-300 mb-4" v-html="getMaterialIcon(selectedMaterial.material_type)"></div>
            <p class="text-xl text-gray-500 mb-2">无法预览此类型的文件</p>
            <p class="text-gray-400 mb-4">{{ selectedMaterial.material_type }} 文件需要下载后查看</p>
            <button 
              @click="downloadMaterial(selectedMaterial.id)" 
              class="px-6 py-2 bg-blue-600 text-white rounded-md"
            >
              下载文件
            </button>
          </div>
        </div>
      </div>
      <div v-else class="flex items-center justify-center h-full">
        <div class="text-center">
          <p class="text-xl text-gray-500 mb-4">请从左侧选择一个文件进行预览</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, defineProps, defineEmits, watch, computed } from 'vue';
import { materialAPI } from '../../api';
import { API_ORIGIN } from '@/config/api';
import { marked } from 'marked';
import DOMPurify from 'dompurify';
import PdfViewer from './PdfViewer.vue';
import MarkdownViewer from './MarkdownViewer.vue';
import DocxViewer from './DocxViewer.vue';
import SpreadsheetViewer from './SpreadsheetViewer.vue';
import PptxViewer from './PptxViewer.vue';

interface Material {
  id: number;
  title: string;
  material_type: string;
  file_path?: string;
  preview_file_path?: string;
  preview_status?: string;
  preview_error?: string | null;
  size: string;
  course_id: number;
  created_at: string;
  updated_at: string;
}

const props = defineProps({
  courseId: {
    type: [Number, String],
    required: true
  },
  initialMaterialId: {
    type: [Number, String, null],
    default: null
  },
  initialPage: {
    type: [Number, String, null],
    default: null
  },
  preferPdfMaterial: {
    type: Boolean,
    default: false
  },
  hideBackButton: {
    type: Boolean,
    default: false
  },
  hideSidebar: {
    type: Boolean,
    default: false
  },
  hidePreviewHeader: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['close']);

const materials = ref<Material[]>([]);
const selectedMaterial = ref<Material | null>(null);
const textContent = ref<string | null>(null);
const markdownContent = ref<string | null>(null);
const resolvedInitialPage = computed(() => {
  const page = Number(props.initialPage);
  return Number.isFinite(page) && page > 0 ? page : 1;
});

// 折叠侧边栏状态
const isSidebarCollapsed = ref(false);
function toggleSidebar() {
  isSidebarCollapsed.value = !isSidebarCollapsed.value;
}

const renderedMarkdown = computed(() => {
  if (!markdownContent.value) return '';
  try {
    // 使用marked将Markdown转换为HTML，并使用DOMPurify进行清洁以防止XSS攻击
    const html = marked.parse(markdownContent.value);
    return typeof html === 'string' ? DOMPurify.sanitize(html) : '';
  } catch (error) {
    console.error('Markdown渲染错误:', error);
    return '无法渲染Markdown内容';
  }
});

onMounted(async () => {
  await syncInitialSelection();
});

async function fetchMaterials() {
  try {
    const response = await materialAPI.getMaterials(Number(props.courseId));
    const responseData = response as any;
    materials.value = responseData.materials as Material[];
  } catch (error) {
    console.error('获取课件资源失败:', error);
  }
}

async function syncInitialSelection() {
  await fetchMaterials();

  if (props.initialMaterialId) {
    const material = materials.value.find(m => m.id === Number(props.initialMaterialId));
    if (material) {
      selectMaterial(material);
      return;
    }
  }

  if (props.preferPdfMaterial) {
    const pdfLikeMaterial = materials.value.find(material => isPdfFile(material) || hasGeneratedPdfPreview(material));
    if (pdfLikeMaterial) {
      selectMaterial(pdfLikeMaterial);
      return;
    }
  }

  if (materials.value.length > 0) {
    selectMaterial(materials.value[0]);
  } else {
    selectedMaterial.value = null;
  }
}

watch(
  () => [props.courseId, props.initialMaterialId, props.preferPdfMaterial],
  async () => {
    await syncInitialSelection();
  }
);

function selectMaterial(material: Material) {
  selectedMaterial.value = material;
  textContent.value = null;
  markdownContent.value = null;
  
  console.log('选择的文件:', material);
  console.log('文件类型:', material.material_type);
  console.log('文件名:', material.title);
  console.log('文件路径:', material.file_path);
  
  // 检查各种文件类型
  console.log('文件类型检测结果:');
  console.log('- PDF:', isPdfFile(material));
  console.log('- Markdown:', isMarkdownFile(material));
  console.log('- 图片:', isImageFile(material));
  console.log('- 视频:', isVideoFile(material));
  console.log('- 文本:', isTextFile(material));
  
  // 检查是否为Markdown文件
  if (isMarkdownFile(material)) {
    console.log('检测到Markdown文件，加载Markdown内容');
    fetchMarkdownContent(material.file_path || '');
  } 
  // 检查是否为文本文件
  else if (isTextFile(material)) {
    console.log('检测到文本文件，加载文本内容');
    fetchTextContent(material.file_path || '');
  }
}

async function fetchTextContent(filePath: string) {
  try {
    const response = await fetch(getFileUrl(filePath));
    if (response.ok) {
      textContent.value = await response.text();
    } else {
      textContent.value = '无法加载文本内容';
    }
  } catch (error) {
    console.error('加载文本内容失败:', error);
    textContent.value = '加载文本内容失败';
  }
}

async function fetchMarkdownContent(filePath: string) {
  try {
    const response = await fetch(getFileUrl(filePath));
    if (response.ok) {
      markdownContent.value = await response.text();
    } else {
      markdownContent.value = '无法加载Markdown内容';
    }
  } catch (error) {
    console.error('加载Markdown内容失败:', error);
    markdownContent.value = '加载Markdown内容失败';
  }
}

function getFileUrl(filePath: string | undefined): string {
  if (!filePath) return '';
  // 确保文件路径以 / 开头
  if (!filePath.startsWith('/')) {
    filePath = '/' + filePath;
  }
  
  // 检查是否已经是完整URL
  if (filePath.startsWith('http://') || filePath.startsWith('https://')) {
    return filePath;
  }
  
  // 使用API服务器地址
  const apiBaseUrl = API_ORIGIN;
  return `${apiBaseUrl}${filePath}`;
}

function downloadMaterial(materialId: number) {
  materialAPI.downloadMaterial(materialId);
}

function closePreview() {
  emit('close');
}

function getMaterialIcon(materialType: string) {
  const type = materialType.toLowerCase();
  switch (type) {
    case 'pdf':
      return `
        <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
        </svg>
      `;
    case 'powerpoint':
      return `
        <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-orange-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
        </svg>
      `;
    case 'word':
      return `
        <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
        </svg>
      `;
    case 'excel':
      return `
        <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
        </svg>
      `;
    case 'image':
      return `
        <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-purple-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
      `;
    case 'video':
      return `
        <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-pink-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
        </svg>
      `;
    case 'archive':
      return `
        <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-amber-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
        </svg>
      `;
    case 'text':
      return `
        <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-gray-900" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      `;
    default:
      return `
        <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
        </svg>
      `;
  }
}

function isMdFile(title: string) {
  // 检查是否为Markdown文件
  return title.toLowerCase().endsWith('.md');
}

function isOfficeDocument(materialType: string) {
  // 检查是否为Office文档类型
  const type = materialType.toLowerCase();
  return type === 'word' || type === 'powerpoint' || type === 'excel' || 
         type === 'docx' || type === 'doc' || type === 'pptx' || type === 'ppt' || 
         type === 'xlsx' || type === 'xls';
}

function getMaterialExtension(material: Material | null) {
  if (!material) return '';
  const title = material.title.toLowerCase();
  const dotIndex = title.lastIndexOf('.');
  return dotIndex >= 0 ? title.slice(dotIndex + 1) : '';
}

function hasGeneratedPdfPreview(material: Material | null) {
  return Boolean(material?.preview_file_path);
}

function getOfficePreviewUrl(material: Material | null) {
  if (!material) return '';
  return getFileUrl(material.preview_file_path || material.file_path || '');
}

function supportsLightweightDocxPreview(material: Material | null) {
  return getMaterialExtension(material) === 'docx';
}

function supportsSpreadsheetPreview(material: Material | null) {
  const extension = getMaterialExtension(material);
  return extension === 'xlsx' || extension === 'xls';
}

function supportsLightweightPptxPreview(material: Material | null) {
  return getMaterialExtension(material) === 'pptx';
}

function getOfficePreviewMessage(material: Material | null) {
  if (!material) return '文档预览不可用';

  const extension = getMaterialExtension(material);

  if (material.preview_status === 'failed') {
    if (extension === 'docx' || extension === 'xlsx' || extension === 'xls' || extension === 'pptx') {
      return '服务端 PDF 预览生成失败，已回退为浏览器轻量预览';
    }
    return '文档预览生成失败，请下载原文件查看';
  }

  if (material.preview_status === 'pending') {
    if (extension === 'docx' || extension === 'xlsx' || extension === 'xls' || extension === 'pptx') {
      return '服务端 PDF 预览正在生成中，如需立即查看可使用浏览器轻量预览';
    }
    return '文档预览正在生成中，请稍后刷新页面';
  }

  if (extension === 'doc') {
    return '旧版 DOC 无法在浏览器内轻量解析，请下载原文件查看';
  }

  if (extension === 'ppt') {
    return '当前环境未安装 Office 转换组件，旧版 PPT 无法在线预览。请先用 PowerPoint 或 WPS 将 .ppt 另存为 .pptx，再重新上传或替换文件。';
  }

  return '文档预览暂不可用，请下载原文件查看';
}

function isPdfFile(material: Material | null) {
  if (!material) return false;
  // 检查文件类型或文件扩展名
  const type = material.material_type.toLowerCase();
  const title = material.title.toLowerCase();
  console.log(`PDF检测: 类型=${type}, 文件名=${title}`);
  return type === 'pdf' || title.endsWith('.pdf');
}

function isImageFile(material: Material | null) {
  if (!material) return false;
  // 检查文件类型或文件扩展名
  const type = material.material_type.toLowerCase();
  const title = material.title.toLowerCase();
  const imageExts = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'];
  return type === 'image' || imageExts.some(ext => title.endsWith(ext));
}

function isVideoFile(material: Material | null) {
  if (!material) return false;
  // 检查文件类型或文件扩展名
  const type = material.material_type.toLowerCase();
  const title = material.title.toLowerCase();
  const videoExts = ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv', '.webm', '.m4v', '.3gp'];
  return type === 'video' || videoExts.some(ext => title.endsWith(ext));
}

function isMarkdownFile(material: Material | null) {
  if (!material) return false;
  // 检查文件类型和文件扩展名
  const type = material.material_type.toLowerCase();
  const title = material.title.toLowerCase();
  console.log(`Markdown检测: 类型=${type}, 文件名=${title}`);
  return type === 'markdown' || title.endsWith('.md') || title.endsWith('.markdown');
}

function isTextFile(material: Material | null) {
  if (!material) return false;
  // 检查文件类型或文件扩展名，但排除Markdown
  const type = material.material_type.toLowerCase();
  const title = material.title.toLowerCase();
  // 如果是Markdown，不算作普通文本
  if (isMarkdownFile(material)) return false;
  const textExts = ['.txt', '.log', '.json', '.xml', '.csv', '.html', '.css', '.js'];
  return type === 'text' || textExts.some(ext => title.endsWith(ext));
}
</script>

<style scoped>
.material-preview-container {
  display: flex;
  height: 100%;
  overflow: hidden;
}

.file-sidebar {
  padding: 1rem 1.5rem; /* default padding, will be zero when collapsed via px-0 */
  border-right: 1px solid #e5e7eb;
  background-color: #f9fafb;
  height: 100%;
  flex-shrink: 0;
}

.file-item {
  transition: all 0.2s;
}

.file-item:hover {
  background-color: #e5e7eb;
}

.preview-area {
  flex: 1;
  padding: 1.5rem;
  overflow-y: auto;
  height: 100%;
  min-width: 0;
}

.preview-area--solo {
  padding: 0;
}

.preview-header {
  margin-bottom: 1.5rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid #e5e7eb;
}

.preview-body {
  min-height: 900px;
}

/* Markdown样式 */
.markdown-body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
  font-size: 16px;
  line-height: 1.6;
  word-wrap: break-word;
}

.markdown-body h1,
.markdown-body h2,
.markdown-body h3,
.markdown-body h4,
.markdown-body h5,
.markdown-body h6 {
  margin-top: 24px;
  margin-bottom: 16px;
  font-weight: 600;
  line-height: 1.25;
}

.markdown-body h1 {
  font-size: 2em;
  border-bottom: 1px solid #eaecef;
  padding-bottom: 0.3em;
}

.markdown-body h2 {
  font-size: 1.5em;
  border-bottom: 1px solid #eaecef;
  padding-bottom: 0.3em;
}

.markdown-body h3 {
  font-size: 1.25em;
}

.markdown-body p,
.markdown-body blockquote,
.markdown-body ul,
.markdown-body ol,
.markdown-body dl,
.markdown-body table,
.markdown-body pre {
  margin-top: 0;
  margin-bottom: 16px;
}

.markdown-body code {
  padding: 0.2em 0.4em;
  margin: 0;
  font-size: 85%;
  background-color: rgba(27, 31, 35, 0.05);
  border-radius: 3px;
}

.markdown-body pre {
  padding: 16px;
  overflow: auto;
  font-size: 85%;
  line-height: 1.45;
  background-color: #f6f8fa;
  border-radius: 3px;
}

.markdown-body pre code {
  display: inline;
  padding: 0;
  margin: 0;
  overflow: visible;
  line-height: inherit;
  word-wrap: normal;
  background-color: transparent;
  border: 0;
}

.markdown-body blockquote {
  padding: 0 1em;
  color: #6a737d;
  border-left: 0.25em solid #dfe2e5;
}

.markdown-body ul,
.markdown-body ol {
  padding-left: 2em;
}

.markdown-body ul {
  list-style-type: disc;
}

.markdown-body ol {
  list-style-type: decimal;
}

.markdown-body table {
  display: block;
  width: 100%;
  overflow: auto;
  border-spacing: 0;
  border-collapse: collapse;
}

.markdown-body table th,
.markdown-body table td {
  padding: 6px 13px;
  border: 1px solid #dfe2e5;
}

.markdown-body table tr {
  background-color: #fff;
  border-top: 1px solid #c6cbd1;
}

.markdown-body table tr:nth-child(2n) {
  background-color: #f6f8fa;
}

.markdown-body img {
  max-width: 100%;
  box-sizing: content-box;
}
</style> 
