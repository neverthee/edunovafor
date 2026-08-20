import { onBeforeUnmount, ref } from 'vue';
import { ragAiAPI } from '@/api';

type AudioSourceKind = 'mic' | 'video';

interface UseAudioTranscriptionOptions {
  filePrefix?: string;
  sourceKind?: AudioSourceKind;
  languageHints?: string[];
  onTranscribed?: (text: string) => void;
  onError?: (message: string, error: unknown) => void;
}

function extractErrorMessage(error: any): string {
  return error?.response?.data?.message || error?.response?.data?.error || error?.message || '未知错误';
}

export function useAudioTranscription(options: UseAudioTranscriptionOptions = {}) {
  const isRecording = ref(false);
  const isTranscribing = ref(false);
  const mediaRecorder = ref<MediaRecorder | null>(null);
  const recordingStream = ref<MediaStream | null>(null);
  const audioChunks = ref<Blob[]>([]);

  function cleanupStream() {
    if (recordingStream.value) {
      recordingStream.value.getTracks().forEach((track) => track.stop());
      recordingStream.value = null;
    }
  }

  function handleError(message: string, error: unknown) {
    if (options.onError) {
      options.onError(message, error);
      return;
    }
    alert(message);
  }

  async function transcribeAudioBlob(audioBlob: Blob) {
    isTranscribing.value = true;
    try {
      const payload = new FormData();
      payload.append('file', audioBlob, `${options.filePrefix || 'audio_input'}_${Date.now()}.webm`);
      payload.append('source_kind', options.sourceKind || 'mic');
      payload.append('language_hints', JSON.stringify(options.languageHints || ['zh', 'en']));

      const response: any = await ragAiAPI.transcribeAudio(payload);
      if (response?.status !== 'success') {
        throw new Error(response?.message || '语音转写失败');
      }

      const text = String(response?.text || '').trim();
      if (text) {
        options.onTranscribed?.(text);
      }
      return text;
    } catch (error) {
      handleError(`语音转写失败: ${extractErrorMessage(error)}`, error);
      return '';
    } finally {
      isTranscribing.value = false;
    }
  }

  async function startRecording() {
    if (isRecording.value || isTranscribing.value) return;

    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
      handleError('当前浏览器不支持语音输入。', null);
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);

      recordingStream.value = stream;
      mediaRecorder.value = recorder;
      audioChunks.value = [];

      recorder.ondataavailable = (event: BlobEvent) => {
        if (event.data && event.data.size > 0) {
          audioChunks.value.push(event.data);
        }
      };

      recorder.onstop = async () => {
        const recordedChunks = [...audioChunks.value];
        audioChunks.value = [];
        cleanupStream();
        mediaRecorder.value = null;
        isRecording.value = false;

        if (!recordedChunks.length) return;
        const audioBlob = new Blob(recordedChunks, { type: recorder.mimeType || 'audio/webm' });
        await transcribeAudioBlob(audioBlob);
      };

      recorder.start();
      isRecording.value = true;
    } catch (error) {
      cleanupStream();
      mediaRecorder.value = null;
      isRecording.value = false;
      handleError('无法启动录音，请检查麦克风权限。', error);
    }
  }

  function stopRecording() {
    if (!mediaRecorder.value || mediaRecorder.value.state === 'inactive') return;
    mediaRecorder.value.stop();
    isRecording.value = false;
  }

  onBeforeUnmount(() => {
    if (mediaRecorder.value && mediaRecorder.value.state !== 'inactive') {
      mediaRecorder.value.stop();
    }
    cleanupStream();
  });

  return {
    isRecording,
    isTranscribing,
    startRecording,
    stopRecording,
    transcribeAudioBlob,
  };
}
