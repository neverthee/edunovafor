<template>
  <div class="pptx-viewer rounded-xl border border-gray-200 bg-white">
    <div v-if="loading" class="flex min-h-[480px] items-center justify-center text-gray-500">
      正在加载演示文稿...
    </div>
    <div v-else-if="error" class="flex min-h-[480px] items-center justify-center px-6 text-center text-gray-500">
      {{ error }}
    </div>
    <div v-else class="space-y-4 p-6">
      <section
        v-for="slide in slides"
        :key="slide.index"
        class="rounded-xl border border-gray-200 bg-gray-50 p-5"
      >
        <h3 class="mb-3 text-base font-semibold text-gray-800">第 {{ slide.index }} 页</h3>
        <ul class="space-y-2 text-gray-700">
          <li v-for="(line, lineIndex) in slide.lines" :key="lineIndex" class="whitespace-pre-wrap break-words">
            {{ line }}
          </li>
        </ul>
        <p v-if="slide.lines.length === 0" class="text-gray-500">该页未提取到可读文本</p>
      </section>
      <p v-if="slides.length === 0" class="text-gray-500">演示文稿内容为空</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import JSZip from 'jszip';

type SlideContent = {
  index: number;
  lines: string[];
};

const props = defineProps<{
  url: string;
}>();

const loading = ref(false);
const error = ref('');
const slides = ref<SlideContent[]>([]);

function extractSlideNumber(path: string) {
  const match = path.match(/slide(\d+)\.xml$/i);
  return match ? Number(match[1]) : 0;
}

function parseSlideText(xmlText: string) {
  const parser = new DOMParser();
  const xml = parser.parseFromString(xmlText, 'application/xml');
  return Array.from(xml.getElementsByTagNameNS('*', 't'))
    .map((node) => (node.textContent || '').trim())
    .filter(Boolean);
}

async function loadPptx() {
  if (!props.url) {
    slides.value = [];
    return;
  }

  loading.value = true;
  error.value = '';

  try {
    const response = await fetch(props.url);
    if (!response.ok) {
      throw new Error('无法加载 PPTX 文件');
    }

    const buffer = await response.arrayBuffer();
    const zip = await JSZip.loadAsync(buffer);
    const slideEntries = Object.keys(zip.files)
      .filter((path) => /^ppt\/slides\/slide\d+\.xml$/i.test(path))
      .sort((left, right) => extractSlideNumber(left) - extractSlideNumber(right));

    const parsedSlides = await Promise.all(
      slideEntries.map(async (path) => {
        const xmlText = await zip.file(path)!.async('text');
        return {
          index: extractSlideNumber(path),
          lines: parseSlideText(xmlText),
        };
      })
    );

    slides.value = parsedSlides;
  } catch (err) {
    console.error('加载 PPTX 失败:', err);
    error.value = err instanceof Error ? err.message : '无法预览该 PPTX 文件';
    slides.value = [];
  } finally {
    loading.value = false;
  }
}

watch(() => props.url, () => {
  loadPptx();
}, { immediate: true });
</script>
