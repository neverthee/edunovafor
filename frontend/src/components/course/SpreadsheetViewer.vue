<template>
  <div class="spreadsheet-viewer rounded-xl border border-gray-200 bg-white">
    <div v-if="loading" class="flex min-h-[480px] items-center justify-center text-gray-500">
      正在加载表格内容...
    </div>
    <div v-else-if="error" class="flex min-h-[480px] items-center justify-center px-6 text-center text-gray-500">
      {{ error }}
    </div>
    <template v-else>
      <div v-if="sheetNames.length > 1" class="flex flex-wrap gap-2 border-b border-gray-200 p-4">
        <button
          v-for="sheetName in sheetNames"
          :key="sheetName"
          type="button"
          @click="activeSheet = sheetName"
          :class="[
            'rounded-full px-3 py-1 text-sm transition',
            activeSheet === sheetName ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700'
          ]"
        >
          {{ sheetName }}
        </button>
      </div>
      <div class="spreadsheet-content overflow-x-auto p-4">
        <div v-html="activeSheetHtml"></div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import DOMPurify from 'dompurify';
import * as XLSX from 'xlsx';

const props = defineProps<{
  url: string;
}>();

const loading = ref(false);
const error = ref('');
const sheetHtmlMap = ref<Record<string, string>>({});
const sheetNames = ref<string[]>([]);
const activeSheet = ref('');

const activeSheetHtml = computed(() => sheetHtmlMap.value[activeSheet.value] || '<p class="text-gray-500">工作表内容为空</p>');

async function loadWorkbook() {
  if (!props.url) {
    sheetHtmlMap.value = {};
    sheetNames.value = [];
    activeSheet.value = '';
    return;
  }

  loading.value = true;
  error.value = '';

  try {
    const response = await fetch(props.url);
    if (!response.ok) {
      throw new Error('无法加载表格文件');
    }

    const buffer = await response.arrayBuffer();
    const workbook = XLSX.read(buffer, { type: 'array' });
    const htmlMap: Record<string, string> = {};

    workbook.SheetNames.forEach((sheetName) => {
      const sheet = workbook.Sheets[sheetName];
      const html = XLSX.utils.sheet_to_html(sheet, { editable: false });
      htmlMap[sheetName] = DOMPurify.sanitize(html);
    });

    sheetHtmlMap.value = htmlMap;
    sheetNames.value = workbook.SheetNames;
    activeSheet.value = workbook.SheetNames[0] || '';
  } catch (err) {
    console.error('加载表格失败:', err);
    error.value = err instanceof Error ? err.message : '无法预览该表格文件';
    sheetHtmlMap.value = {};
    sheetNames.value = [];
    activeSheet.value = '';
  } finally {
    loading.value = false;
  }
}

watch(() => props.url, () => {
  loadWorkbook();
}, { immediate: true });
</script>

<style scoped>
.spreadsheet-content :deep(table) {
  min-width: 100%;
  border-collapse: collapse;
}

.spreadsheet-content :deep(td),
.spreadsheet-content :deep(th) {
  border: 1px solid #e5e7eb;
  padding: 0.5rem 0.75rem;
  vertical-align: top;
}

.spreadsheet-content :deep(tr:nth-child(even)) {
  background: #f9fafb;
}
</style>
