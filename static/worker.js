// WhisperFlow In-Browser Web Worker for Client-Side GPU (WebGPU) and CPU (WASM) Transcription
// Powered by Hugging Face Transformers.js (ONNX Runtime Web)

import { pipeline, env } from 'https://cdn.jsdelivr.net/npm/@huggingface/transformers@3.3.3';

// Configure Transformers.js runtime
env.allowLocalModels = false;
env.useBrowserCache = true;

let transcriber = null;
let currentModelKey = null;
let currentDeviceKey = null;

// Map user model selection to ONNX Community Whisper models
const MODEL_MAPPING = {
  'tiny': 'onnx-community/whisper-tiny',
  'base': 'onnx-community/whisper-base',
  'small': 'onnx-community/whisper-small',
  'medium': 'onnx-community/whisper-base', // fallback to base for in-browser memory safety
  'large-v3-turbo': 'onnx-community/whisper-small',
  'large-v3': 'onnx-community/whisper-small'
};

async function getTranscriber(modelSize, requestedDevice) {
  const modelName = MODEL_MAPPING[modelSize] || MODEL_MAPPING['base'];
  const cacheKey = `${modelName}_${requestedDevice}`;

  if (transcriber && currentModelKey === cacheKey) {
    return { transcriber, device: currentDeviceKey };
  }

  // Attempt WebGPU first if requested or auto
  let actualDevice = 'wasm';
  let dtype = 'q8';

  if (requestedDevice === 'webgpu' || requestedDevice === 'cuda' || requestedDevice === 'auto') {
    try {
      self.postMessage({
        type: 'status',
        message: 'Initializing WebGPU acceleration for your GPU...'
      });

      transcriber = await pipeline('automatic-speech-recognition', modelName, {
        device: 'webgpu',
        dtype: {
          encoder_model: 'fp32',
          decoder_model_merged: 'q4'
        },
        progress_callback: (progressData) => {
          self.postMessage({ type: 'progress', data: progressData });
        }
      });

      actualDevice = 'webgpu';
      currentModelKey = cacheKey;
      currentDeviceKey = 'webgpu';

      self.postMessage({
        type: 'status',
        message: 'WebGPU Pipeline Ready (Hardware GPU Acceleration Active)'
      });

      return { transcriber, device: 'webgpu' };
    } catch (gpuError) {
      console.warn('WebGPU initialization failed or not supported by browser, falling back to WebAssembly CPU:', gpuError);
      self.postMessage({
        type: 'status',
        message: 'WebGPU unavailable on this device/browser. Falling back to multi-threaded CPU (WebAssembly)...'
      });
    }
  }

  // Fallback to CPU WebAssembly
  actualDevice = 'wasm';
  dtype = 'q8';

  self.postMessage({
    type: 'status',
    message: 'Loading model for multi-threaded CPU inference...'
  });

  transcriber = await pipeline('automatic-speech-recognition', modelName, {
    device: 'wasm',
    dtype: dtype,
    progress_callback: (progressData) => {
      self.postMessage({ type: 'progress', data: progressData });
    }
  });

  currentModelKey = cacheKey;
  currentDeviceKey = 'wasm';

  self.postMessage({
    type: 'status',
    message: 'WebAssembly CPU Pipeline Ready'
  });

  return { transcriber, device: 'wasm' };
}

self.addEventListener('message', async (e) => {
  const { type, data } = e.data;

  if (type === 'load') {
    try {
      const { modelSize, device } = data;
      await getTranscriber(modelSize, device);
      self.postMessage({ type: 'ready' });
    } catch (err) {
      self.postMessage({ type: 'error', error: err.message || 'Failed to initialize Whisper model.' });
    }
    return;
  }

  if (type === 'transcribe') {
    try {
      const {
        audio,
        modelSize,
        device,
        language,
        task,
        chunk_length_s = 30,
        stride_length_s = 5
      } = data;

      self.postMessage({
        type: 'status',
        message: 'Preparing model and allocating memory...'
      });

      const { transcriber: pipelineInstance, device: activeDev } = await getTranscriber(modelSize, device);

      self.postMessage({
        type: 'status',
        message: `Transcribing audio using client ${activeDev === 'webgpu' ? 'GPU (WebGPU)' : 'CPU (WebAssembly)'}...`
      });

      const options = {
        chunk_length_s: chunk_length_s,
        stride_length_s: stride_length_s,
        return_timestamps: true,
        task: task || 'transcribe'
      };

      if (language && language !== 'auto') {
        options.language = language;
      }

      const startTime = performance.now();
      const output = await pipelineInstance(audio, options);
      const executionTime = ((performance.now() - startTime) / 1000).toFixed(2);

      // Normalize output chunks
      let chunks = [];
      if (Array.isArray(output.chunks) && output.chunks.length > 0) {
        chunks = output.chunks.map((c, idx) => ({
          id: idx,
          start: Array.isArray(c.timestamp) ? c.timestamp[0] ?? 0 : (idx * 5),
          end: Array.isArray(c.timestamp) ? c.timestamp[1] ?? ((c.timestamp[0] ?? 0) + 2) : ((idx + 1) * 5),
          text: (c.text || '').trim()
        })).filter(c => c.text.length > 0);
      } else {
        chunks = [{
          id: 0,
          start: 0,
          end: Math.max(1, audio.length / 16000),
          text: (output.text || '').trim()
        }];
      }

      self.postMessage({
        type: 'complete',
        result: {
          full_text: output.text ? output.text.trim() : chunks.map(c => c.text).join(' '),
          segments: chunks,
          device_used: activeDev === 'webgpu' ? 'WebGPU (Client GPU)' : 'CPU (Client WebAssembly)',
          execution_time: executionTime
        }
      });

    } catch (err) {
      console.error('Transcription error inside worker:', err);
      self.postMessage({
        type: 'error',
        error: err.message || 'An error occurred during in-browser transcription.'
      });
    }
  }
});
