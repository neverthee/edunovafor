<template>
  <div class="docx-viewer rounded-xl border border-gray-200 bg-white">
    <div v-if="loading" class="flex min-h-[480px] items-center justify-center text-gray-500">
      正在加载文档内容...
    </div>
    <div v-else-if="error" class="flex min-h-[480px] items-center justify-center px-6 text-center text-gray-500">
      {{ error }}
    </div>
    <div v-else class="space-y-4 p-6">
      <template v-for="(block, index) in blocks" :key="index">
        <p v-if="block.type === 'paragraph'" class="whitespace-pre-wrap break-words text-gray-800">
          {{ block.text || ' ' }}
        </p>
        <div v-else-if="block.type === 'image'" class="overflow-hidden rounded-lg border border-gray-200 bg-gray-50 p-3">
          <img :src="block.src" :alt="block.alt" class="mx-auto max-w-full h-auto" loading="lazy" />
        </div>
        <div v-else class="overflow-x-auto">
          <table class="min-w-full border-collapse text-sm">
            <tbody>
              <tr v-for="(row, rowIndex) in block.rows" :key="rowIndex">
                <td
                  v-for="(cell, cellIndex) in row"
                  :key="cellIndex"
                  class="border border-gray-200 px-3 py-2 align-top text-gray-700"
                >
                  {{ cell }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
      <p v-if="blocks.length === 0" class="text-gray-500">文档内容为空</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue';
import JSZip from 'jszip';

type ParagraphBlock = { type: 'paragraph'; text: string };
type ImageBlock = { type: 'image'; src: string; alt: string };
type TableBlock = { type: 'table'; rows: string[][] };
type DocxBlock = ParagraphBlock | ImageBlock | TableBlock;
type ParagraphToken =
  | { type: 'text'; value: string }
  | { type: 'image'; relationshipId: string; alt: string };

const props = defineProps<{
  url: string;
}>();

const loading = ref(false);
const error = ref('');
const blocks = ref<DocxBlock[]>([]);
const activeBlobUrls: string[] = [];

function revokeBlobUrls() {
  while (activeBlobUrls.length > 0) {
    const url = activeBlobUrls.pop();
    if (url) {
      URL.revokeObjectURL(url);
    }
  }
}

function getChildElements(node: Element, localName: string) {
  return Array.from(node.childNodes).filter(
    (child): child is Element => child.nodeType === Node.ELEMENT_NODE && (child as Element).localName === localName
  );
}

function getAttributeByLocalName(node: Element, localName: string) {
  return Array.from(node.attributes).find((attribute) => attribute.localName === localName)?.value || '';
}

function normalizeZipPath(path: string) {
  const parts: string[] = [];

  path.replace(/\\/g, '/').split('/').forEach((part) => {
    if (!part || part === '.') return;
    if (part === '..') {
      parts.pop();
      return;
    }
    parts.push(part);
  });

  return parts.join('/');
}

function resolveZipPath(baseDirectory: string, target: string) {
  if (!target || /^[a-z]+:/i.test(target)) {
    return '';
  }

  if (target.startsWith('/')) {
    return normalizeZipPath(target.slice(1));
  }

  return normalizeZipPath(`${baseDirectory}/${target}`);
}

function collectText(node: Element): string {
  const parts: string[] = [];

  const walk = (current: Element) => {
    if (current.localName === 't') {
      parts.push(current.textContent || '');
      return;
    }

    if (current.localName === 'tab') {
      parts.push('\t');
      return;
    }

    if (current.localName === 'br' || current.localName === 'cr') {
      parts.push('\n');
      return;
    }

    Array.from(current.childNodes).forEach((child) => {
      if (child.nodeType === Node.ELEMENT_NODE) {
        walk(child as Element);
      }
    });
  };

  walk(node);
  return parts.join('').trim();
}

function collectParagraphTokens(node: Element): ParagraphToken[] {
  const tokens: ParagraphToken[] = [];

  const walk = (current: Element) => {
    if (current.localName === 't') {
      tokens.push({ type: 'text', value: current.textContent || '' });
      return;
    }

    if (current.localName === 'tab') {
      tokens.push({ type: 'text', value: '\t' });
      return;
    }

    if (current.localName === 'br' || current.localName === 'cr') {
      tokens.push({ type: 'text', value: '\n' });
      return;
    }

    if (current.localName === 'blip') {
      const relationshipId = getAttributeByLocalName(current, 'embed') || getAttributeByLocalName(current, 'link');
      if (relationshipId) {
        tokens.push({ type: 'image', relationshipId, alt: '文档图片' });
      }
      return;
    }

    if (current.localName === 'imagedata') {
      const relationshipId = getAttributeByLocalName(current, 'id');
      const alt = getAttributeByLocalName(current, 'title') || '文档图片';
      if (relationshipId) {
        tokens.push({ type: 'image', relationshipId, alt });
      }
      return;
    }

    Array.from(current.childNodes).forEach((child) => {
      if (child.nodeType === Node.ELEMENT_NODE) {
        walk(child as Element);
      }
    });
  };

  walk(node);
  return tokens;
}

async function buildImageRelationshipMap(zip: JSZip) {
  const relsFile = zip.file('word/_rels/document.xml.rels');
  const relationships = new Map<string, string>();

  if (!relsFile) {
    return relationships;
  }

  const relsXmlText = await relsFile.async('text');
  const parser = new DOMParser();
  const relsXml = parser.parseFromString(relsXmlText, 'application/xml');

  Array.from(relsXml.getElementsByTagNameNS('*', 'Relationship')).forEach((relationship) => {
    const relationshipType = relationship.getAttribute('Type') || '';
    const relationshipId = relationship.getAttribute('Id') || '';
    const target = relationship.getAttribute('Target') || '';

    if (!relationshipId || !relationshipType.includes('/image')) {
      return;
    }

    const resolvedPath = resolveZipPath('word', target);
    if (resolvedPath) {
      relationships.set(relationshipId, resolvedPath);
    }
  });

  return relationships;
}

async function buildImageSourceResolver(zip: JSZip, relationshipMap: Map<string, string>) {
  const sourceCache = new Map<string, string | null>();

  return async (relationshipId: string) => {
    if (!relationshipId) {
      return null;
    }

    if (sourceCache.has(relationshipId)) {
      return sourceCache.get(relationshipId) || null;
    }

    const zipPath = relationshipMap.get(relationshipId);
    if (!zipPath) {
      sourceCache.set(relationshipId, null);
      return null;
    }

    const file = zip.file(zipPath);
    if (!file) {
      sourceCache.set(relationshipId, null);
      return null;
    }

    const blob = await file.async('blob');
    const objectUrl = URL.createObjectURL(blob);
    activeBlobUrls.push(objectUrl);
    sourceCache.set(relationshipId, objectUrl);
    return objectUrl;
  };
}

async function parseDocument(xmlText: string, zip: JSZip): Promise<DocxBlock[]> {
  const parser = new DOMParser();
  const xml = parser.parseFromString(xmlText, 'application/xml');
  const body = xml.getElementsByTagNameNS('*', 'body')[0];
  if (!body) return [];

  const relationshipMap = await buildImageRelationshipMap(zip);
  const resolveImageSource = await buildImageSourceResolver(zip, relationshipMap);
  const result: DocxBlock[] = [];

  for (const child of Array.from(body.childNodes)) {
    if (child.nodeType !== Node.ELEMENT_NODE) continue;
    const element = child as Element;

    if (element.localName === 'p') {
      const tokens = collectParagraphTokens(element);
      let paragraphText = '';
      let emittedBlock = false;

      const flushParagraphText = () => {
        if (paragraphText.length === 0) {
          return;
        }
        result.push({ type: 'paragraph', text: paragraphText });
        paragraphText = '';
        emittedBlock = true;
      };

      for (const token of tokens) {
        if (token.type === 'text') {
          paragraphText += token.value;
          continue;
        }

        flushParagraphText();
        const imageSource = await resolveImageSource(token.relationshipId);
        if (imageSource) {
          result.push({ type: 'image', src: imageSource, alt: token.alt || '文档图片' });
          emittedBlock = true;
        }
      }

      flushParagraphText();
      if (!emittedBlock) {
        result.push({ type: 'paragraph', text: collectText(element) });
      }
      continue;
    }

    if (element.localName === 'tbl') {
      const rows = getChildElements(element, 'tr').map((row) =>
        getChildElements(row, 'tc').map((cell) =>
          getChildElements(cell, 'p')
            .map((paragraph) => collectText(paragraph))
            .filter(Boolean)
            .join('\n')
          )
      );
      result.push({ type: 'table', rows });
    }
  }

  return result;
}

async function loadDocx() {
  if (!props.url) {
    revokeBlobUrls();
    blocks.value = [];
    return;
  }

  loading.value = true;
  error.value = '';
  revokeBlobUrls();

  try {
    const response = await fetch(props.url);
    if (!response.ok) {
      throw new Error('无法加载 DOCX 文件');
    }

    const buffer = await response.arrayBuffer();
    const zip = await JSZip.loadAsync(buffer);
    const documentFile = zip.file('word/document.xml');
    if (!documentFile) {
      throw new Error('DOCX 结构不完整，未找到正文');
    }

    const xmlText = await documentFile.async('text');
    blocks.value = await parseDocument(xmlText, zip);
  } catch (err) {
    console.error('加载 DOCX 失败:', err);
    error.value = err instanceof Error ? err.message : '无法预览该 DOCX 文件';
    blocks.value = [];
  } finally {
    loading.value = false;
  }
}

watch(() => props.url, () => {
  loadDocx();
}, { immediate: true });

onBeforeUnmount(() => {
  revokeBlobUrls();
});
</script>
