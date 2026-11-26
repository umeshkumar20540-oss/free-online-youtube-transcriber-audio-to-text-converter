// WhisperFlow: In-Browser AI YouTube & Audio Transcriber
// 100% Client-Side WebGPU & CPU Multi-Threaded WASM Inference

let activeWorker = null;
let currentAudioBuffer = null;
let currentAudioFloat32 = null;
let currentAudioBlob = null;
let currentAudioDuration = 0;
let currentMediaTitle = "Sample Audio";
let currentMediaAuthor = "Local User";
let currentMediaThumbnail = "";
let currentSegments = [];
let currentFullText = "";
let currentRecordId = null;

let isRecordingMic = false;
let mediaRecorder = null;
let recordedChunks = [];
let micTimerInterval = null;
let micSeconds = 0;

// DOM Elements
const themeToggleBtn = document.getElementById('themeToggleBtn');
const hardwareBadge = document.getElementById('hardwareBadge');
const hardwareText = document.getElementById('hardwareText');
const hardwareDot = document.getElementById('hardwareDot');
const hardwarePing = document.getElementById('hardwarePing');

const tabYoutube = document.getElementById('tabYoutube');
const tabLocal = document.getElementById('tabLocal');
const tabMic = document.getElementById('tabMic');
const youtubePanel = document.getElementById('youtubePanel');
const localPanel = document.getElementById('localPanel');
const micPanel = document.getElementById('micPanel');

const youtubeUrlInput = document.getElementById('youtubeUrlInput');
const fetchInfoBtn = document.getElementById('fetchInfoBtn');
const videoPreviewCard = document.getElementById('videoPreviewCard');
const videoPreviewThumbnail = document.getElementById('videoPreviewThumbnail');
const videoPreviewTitle = document.getElementById('videoPreviewTitle');
const videoPreviewChannelVal = document.getElementById('videoPreviewChannelVal');
const videoPreviewDurationVal = document.getElementById('videoPreviewDurationVal');
const youtubeStatusBadge = document.getElementById('youtubeStatusBadge');

const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const uploadSelectedInfo = document.getElementById('uploadSelectedInfo');
const uploadFileName = document.getElementById('uploadFileName');

const micRecordBtn = document.getElementById('micRecordBtn');
const micStatusTitle = document.getElementById('micStatusTitle');
const micTimer = document.getElementById('micTimer');
const micRecordingBadge = document.getElementById('micRecordingBadge');

const quickDemoBtn = document.getElementById('quickDemoBtn');
const modelSelect = document.getElementById('modelSelect');
const languageSelect = document.getElementById('languageSelect');
const taskSelect = document.getElementById('taskSelect');
const deviceSelect = document.getElementById('deviceSelect');
const startTranscribeBtn = document.getElementById('startTranscribeBtn');

const progressCard = document.getElementById('progressCard');
const progressStatusText = document.getElementById('progressStatusText');
const progressSubText = document.getElementById('progressSubText');
const progressPctText = document.getElementById('progressPctText');
const progressBarFill = document.getElementById('progressBarFill');
const liveStreamTerminal = document.getElementById('liveStreamTerminal');

const resultsCard = document.getElementById('resultsCard');
const resultTitle = document.getElementById('resultTitle');
const resultAuthor = document.getElementById('resultAuthor');
const resultLangBadge = document.getElementById('resultLangBadge');
const resultModelBadge = document.getElementById('resultModelBadge');
const resultDurationBadge = document.getElementById('resultDurationBadge');
const audioPlayer = document.getElementById('audioPlayer');

const viewTabSegments = document.getElementById('viewTabSegments');
const viewTabText = document.getElementById('viewTabText');
const viewTabSummary = document.getElementById('viewTabSummary');
const viewContainerSegments = document.getElementById('viewContainerSegments');
const viewContainerText = document.getElementById('viewContainerText');
const viewContainerSummary = document.getElementById('viewContainerSummary');
const continuousTextContent = document.getElementById('continuousTextContent');
const summaryContent = document.getElementById('summaryContent');
const transcriptSearchInput = document.getElementById('transcriptSearchInput');
const searchMatchCount = document.getElementById('searchMatchCount');

const exportDropdownBtn = document.getElementById('exportDropdownBtn');
const exportMenu = document.getElementById('exportMenu');
const copyAllBtn = document.getElementById('copyAllBtn');

const openHistoryBtn = document.getElementById('openHistoryBtn');
const closeHistoryBtn = document.getElementById('closeHistoryBtn');
const historyDrawerBackdrop = document.getElementById('historyDrawerBackdrop');
const historyListContainer = document.getElementById('historyListContainer');
const historySearchInput = document.getElementById('historySearchInput');
const historyCountBadge = document.getElementById('historyCountBadge');

// 1. Theme Management & Server Config
const serverConfigBtn = document.getElementById('serverConfigBtn');
if (serverConfigBtn) {
  serverConfigBtn.addEventListener('click', () => {
    const cur = localStorage.getItem('whisperflow_backend_url') || 'https://youtube.minimaxtools.com';
    const next = prompt("Enter your Python / Colab Backend URL (HTTPS):\n(Leave default or update whenever Colab restarts)", cur);
    if (next !== null && next.trim()) {
      localStorage.setItem('whisperflow_backend_url', next.trim().replace(/\/$/, ''));
      showToast('Backend URL updated to ' + next.trim(), 'success');
    }
  });
}

// Clear Browser Cache & Model Memory
const clearCacheBtn = document.getElementById('clearCacheBtn');
if (clearCacheBtn) {
  clearCacheBtn.addEventListener('click', async () => {
    if (confirm('Clear all downloaded AI models and browser memory? (Ensures 100% clean state, no old data)')) {
      try {
        if (window.caches) {
          const keys = await caches.keys();
          for (const k of keys) await caches.delete(k);
        }
        showToast('Browser cache and models cleared!', 'success');
        setTimeout(() => location.reload(), 600);
      } catch (e) {
        showToast('Error clearing cache: ' + e.message, 'error');
      }
    }
  });
}
function initTheme() {
  const saved = localStorage.getItem('whisperflow_theme') || 'dark';
  if (saved === 'dark') {
    document.documentElement.classList.add('dark');
  } else {
    document.documentElement.classList.remove('dark');
  }
}

themeToggleBtn.addEventListener('click', () => {
  const isDark = document.documentElement.classList.toggle('dark');
  localStorage.setItem('whisperflow_theme', isDark ? 'dark' : 'light');
});

// 2. Hardware Detection
async function detectHardware() {
  if (navigator.gpu) {
    try {
      const adapter = await navigator.gpu.requestAdapter({ powerPreference: 'high-performance' });
      if (adapter) {
        let desc = "Hardware GPU Acceleration";
        if (adapter.info && adapter.info.description) {
          desc = adapter.info.description;
        } else if (adapter.info && adapter.info.vendor) {
          desc = `${adapter.info.vendor} GPU`;
        }
        hardwareText.innerHTML = `<span class="text-emerald-400 font-semibold">WebGPU Active</span>: ${desc}`;
        hardwareBadge.classList.remove('hidden');
        return 'webgpu';
      }
    } catch (e) {
      console.warn("WebGPU access failed:", e);
    }
  }

  // CPU fallback
  const threads = navigator.hardwareConcurrency || 4;
  hardwareText.innerHTML = `<span class="text-indigo-400 font-semibold">CPU Mode</span>: ${threads} Threads (WASM SIMD)`;
  if (hardwareDot) hardwareDot.className = "relative inline-flex rounded-full h-2 w-2 bg-indigo-500";
  if (hardwarePing) hardwarePing.className = "animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75";
  hardwareBadge.classList.remove('hidden');
  return 'wasm';
}

// 3. Tab Switching
function switchTab(active) {
  [tabYoutube, tabLocal, tabMic].forEach(t => {
    t.className = "px-4 py-2 rounded-lg text-sm font-semibold text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-surface-800 flex items-center space-x-2 transition";
  });
  [youtubePanel, localPanel, micPanel].forEach(p => p.classList.add('hidden'));

  if (active === 'youtube') {
    tabYoutube.className = "px-4 py-2 rounded-lg text-sm font-semibold bg-brand-600 text-white flex items-center space-x-2 transition";
    youtubePanel.classList.remove('hidden');
  } else if (active === 'local') {
    tabLocal.className = "px-4 py-2 rounded-lg text-sm font-semibold bg-brand-600 text-white flex items-center space-x-2 transition";
    localPanel.classList.remove('hidden');
  } else if (active === 'mic') {
    tabMic.className = "px-4 py-2 rounded-lg text-sm font-semibold bg-brand-600 text-white flex items-center space-x-2 transition";
    micPanel.classList.remove('hidden');
  }
}

tabYoutube.addEventListener('click', () => switchTab('youtube'));
tabLocal.addEventListener('click', () => switchTab('local'));
tabMic.addEventListener('click', () => switchTab('mic'));

// 4. Audio Processing Helpers (Web Audio API)
async function decodeAudioFile(fileOrBlob) {
  const arrayBuffer = await fileOrBlob.arrayBuffer();
  const tempCtx = new (window.AudioContext || window.webkitAudioContext)();
  const decoded = await tempCtx.decodeAudioData(arrayBuffer);
  await tempCtx.close().catch(() => {});

  currentAudioDuration = decoded.duration;
  if (videoPreviewDurationVal) {
    videoPreviewDurationVal.textContent = formatTime(currentAudioDuration);
  }

  // Guarantee exact 16kHz mono Float32Array via OfflineAudioContext
  let float32Array;
  if (decoded.sampleRate === 16000 && decoded.numberOfChannels === 1) {
    float32Array = decoded.getChannelData(0);
  } else {
    const targetLength = Math.max(1, Math.ceil(decoded.duration * 16000));
    const offlineCtx = new OfflineAudioContext(1, targetLength, 16000);
    const source = offlineCtx.createBufferSource();
    source.buffer = decoded;
    source.connect(offlineCtx.destination);
    source.start(0);
    const rendered = await offlineCtx.startRendering();
    float32Array = rendered.getChannelData(0);
  }

  currentAudioFloat32 = float32Array;
  currentAudioBlob = fileOrBlob;
  audioPlayer.src = URL.createObjectURL(fileOrBlob);
  audioPlayer.load();

  return float32Array;
}

// 5. Local File Upload
dropZone.addEventListener('click', () => fileInput.click());

['dragenter', 'dragover'].forEach(name => {
  dropZone.addEventListener(name, (e) => {
    e.preventDefault();
    dropZone.classList.add('dropzone-active');
  });
});

['dragleave', 'drop'].forEach(name => {
  dropZone.addEventListener(name, (e) => {
    e.preventDefault();
    dropZone.classList.remove('dropzone-active');
  });
});

dropZone.addEventListener('drop', (e) => {
  if (e.dataTransfer.files && e.dataTransfer.files[0]) {
    handleLocalFile(e.dataTransfer.files[0]);
  }
});

fileInput.addEventListener('change', () => {
  if (fileInput.files && fileInput.files[0]) {
    handleLocalFile(fileInput.files[0]);
  }
});

async function handleLocalFile(file) {
  uploadFileName.textContent = `Decoding ${file.name}...`;
  uploadSelectedInfo.classList.remove('hidden');

  try {
    currentMediaTitle = file.name.replace(/\.[^/.]+$/, "");
    currentMediaAuthor = "Uploaded Audio File";
    await decodeAudioFile(file);
    uploadFileName.textContent = `${file.name} (${formatTime(currentAudioDuration)}) - Ready!`;
    showToast('File decoded and ready for transcription!', 'success');
  } catch (err) {
    uploadSelectedInfo.classList.add('hidden');
    showToast('Failed to decode audio: ' + err.message, 'error');
  }
}

// 6. YouTube URL Extraction & Handling
function extractYouTubeId(url) {
  const match = url.match(/(?:youtu\.be\/|youtube\.com\/(?:watch\?v=|shorts\/|embed\/))([a-zA-Z0-9_-]{11})/);
  return match ? match[1] : null;
}

async function handleYouTubeUrl() {
  const url = youtubeUrlInput.value.trim();
  const videoId = extractYouTubeId(url);

  if (!videoId) {
    showToast('Please enter a valid YouTube video URL or ID.', 'error');
    return;
  }

  fetchInfoBtn.disabled = true;
  fetchInfoBtn.innerHTML = `<i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i><span>Loading...</span>`;
  lucide.createIcons();

  let ytTimerInterval = null;
  const startTimerMs = Date.now();

  try {
    currentMediaThumbnail = `https://img.youtube.com/vi/${videoId}/hqdefault.jpg`;
    videoPreviewThumbnail.src = currentMediaThumbnail;
    videoPreviewTitle.textContent = `YouTube Video (${videoId})`;
    videoPreviewChannelVal.textContent = "YouTube Creator";
    videoPreviewDurationVal.textContent = "Loading...";

    // Fetch oEmbed metadata (CORS-friendly public endpoint)
    try {
      const oembedRes = await fetch(`https://noembed.com/embed?url=https://www.youtube.com/watch?v=${videoId}`);
      if (oembedRes.ok) {
        const meta = await oembedRes.json();
        if (meta.title) videoPreviewTitle.textContent = meta.title;
        if (meta.author_name) videoPreviewChannelVal.textContent = meta.author_name;
        currentMediaTitle = meta.title || `YouTube Video (${videoId})`;
        currentMediaAuthor = meta.author_name || "YouTube Creator";
      }
    } catch (e) {
      console.warn("oEmbed fetch failed:", e);
    }

    videoPreviewCard.classList.remove('hidden');

    // Rich Live Progress UI with live elapsed timer, MB counter, and percentage
    youtubeStatusBadge.innerHTML = `
      <div class="mt-3 p-3.5 rounded-xl bg-slate-900/95 border border-slate-700/80 space-y-2.5">
        <div class="flex items-center justify-between text-xs">
          <span class="flex items-center space-x-2 text-brand-300 font-semibold" id="ytStatusPhaseText">
            <i data-lucide="loader-2" class="w-4 h-4 animate-spin text-brand-400"></i>
            <span>1. Connecting to Cloud Server &amp; Extracting Lightweight AAC Audio...</span>
          </span>
          <span id="ytTimerDisplay" class="text-slate-400 font-mono text-[11px]">Elapsed: 00:00</span>
        </div>
        <!-- Progress Bar -->
        <div class="w-full bg-slate-800 rounded-full h-2 overflow-hidden border border-slate-700">
          <div id="ytProgressBar" class="bg-gradient-to-r from-brand-500 to-emerald-400 h-2 rounded-full transition-all duration-150 animate-pulse" style="width: 15%"></div>
        </div>
        <div class="flex items-center justify-between text-[11px] text-slate-400">
          <span id="ytStatusDetailText">Downloading AAC/M4A audio only (Ultra-lightweight ~15-20MB)...</span>
          <span id="ytStatusSpeedText" class="font-mono text-emerald-400 text-[10px]">Fast Stream</span>
        </div>
      </div>
    `;
    lucide.createIcons();

    // Start live elapsed timer
    ytTimerInterval = setInterval(() => {
      const elapsedSec = Math.floor((Date.now() - startTimerMs) / 1000);
      const timerEl = document.getElementById('ytTimerDisplay');
      if (timerEl) {
        const m = Math.floor(elapsedSec / 60).toString().padStart(2, '0');
        const s = (elapsedSec % 60).toString().padStart(2, '0');
        timerEl.textContent = `Elapsed: ${m}:${s}`;
      }
    }, 1000);

    // 1. First attempt: Dedicated Cloud Backend (Google Colab / Cloudflare Tunnel)
    let audioBlobLoaded = false;
    let finalAudioBlob = null;
    let backendErrorMsg = '';
    const backendUrl = localStorage.getItem('whisperflow_backend_url') || 'https://youtube.minimaxtools.com';

    if (backendUrl) {
      try {
        const cloudRes = await fetch(`${backendUrl}/api/audio`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url: `https://www.youtube.com/watch?v=${videoId}` })
        });

        if (cloudRes.ok) {
          const contentLength = cloudRes.headers.get('Content-Length');
          const totalBytes = contentLength ? parseInt(contentLength, 10) : 0;
          const serverDuration = cloudRes.headers.get('X-Audio-Duration');
          const rawTitle = cloudRes.headers.get('X-Audio-Title');
          const rawUploader = cloudRes.headers.get('X-Audio-Uploader');

          if (serverDuration && !isNaN(serverDuration)) {
            videoPreviewDurationVal.textContent = formatTime(parseFloat(serverDuration));
          }
          if (rawTitle && rawTitle.trim()) {
            try {
              const decodedTitle = decodeURIComponent(rawTitle.trim());
              videoPreviewTitle.textContent = decodedTitle;
              currentMediaTitle = decodedTitle;
            } catch (e) {
              videoPreviewTitle.textContent = rawTitle.trim();
              currentMediaTitle = rawTitle.trim();
            }
          }
          if (rawUploader && rawUploader.trim()) {
            try {
              const decodedUploader = decodeURIComponent(rawUploader.trim());
              videoPreviewChannelVal.textContent = decodedUploader;
              currentMediaAuthor = decodedUploader;
            } catch (e) {
              videoPreviewChannelVal.textContent = rawUploader.trim();
              currentMediaAuthor = rawUploader.trim();
            }
          }

          const phaseText = document.getElementById('ytStatusPhaseText');
          const detailText = document.getElementById('ytStatusDetailText');
          const speedText = document.getElementById('ytStatusSpeedText');
          const bar = document.getElementById('ytProgressBar');

          if (bar) bar.classList.remove('animate-pulse');
          if (phaseText) {
            phaseText.innerHTML = `<i data-lucide="download-cloud" class="w-4 h-4 text-emerald-400"></i><span>2. Streaming Lightweight AAC Audio to Browser...</span>`;
            lucide.createIcons();
          }

          // Use ReadableStream for real-time bytes & percentage progress
          const reader = cloudRes.body.getReader();
          const chunks = [];
          let receivedBytes = 0;
          const streamStart = Date.now();

          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            chunks.push(value);
            receivedBytes += value.length;

            const streamSec = (Date.now() - streamStart) / 1000;
            const mbRecv = (receivedBytes / 1048576).toFixed(1);
            const speed = streamSec > 0.2 ? ((receivedBytes / 1048576) / streamSec).toFixed(1) : '1.5';

            if (totalBytes > 0 && bar) {
              const pct = Math.min(100, Math.round((receivedBytes / totalBytes) * 100));
              bar.style.width = `${pct}%`;
              if (detailText) detailText.textContent = `Streaming AAC: ${mbRecv} MB / ${(totalBytes / 1048576).toFixed(1)} MB (${pct}%)`;
            } else {
              if (bar) bar.style.width = '70%';
              if (detailText) detailText.textContent = `Streaming AAC: ${mbRecv} MB received`;
            }
            if (speedText) speedText.textContent = `${speed} MB/s`;
          }

          const contentType = cloudRes.headers.get('Content-Type') || 'audio/mp4';
          finalAudioBlob = new Blob(chunks, { type: contentType });

          // Phase 3: Decoding into WebGPU audio buffer
          if (phaseText) {
            phaseText.innerHTML = `<i data-lucide="cpu" class="w-4 h-4 text-brand-400 animate-spin"></i><span>3. Decoding AAC Audio into WebGPU Audio Buffer...</span>`;
            lucide.createIcons();
          }
          if (detailText) detailText.textContent = `Preparing 16kHz mono audio tensor for in-browser AI...`;
          if (bar) bar.style.width = '95%';

          await decodeAudioFile(finalAudioBlob);
          audioBlobLoaded = true;
        } else {
          try {
            const errJson = await cloudRes.json();
            backendErrorMsg = errJson.detail || `Server error (${cloudRes.status})`;
          } catch (e) {
            backendErrorMsg = `Server returned HTTP ${cloudRes.status}`;
          }
        }
      } catch (backendErr) {
        console.warn("Colab Cloud backend unreachable or error:", backendErr);
        backendErrorMsg = backendErr.message || "Backend unreachable";
      }
    }

    if (ytTimerInterval) clearInterval(ytTimerInterval);

    if (audioBlobLoaded && finalAudioBlob) {
      const mbSize = (finalAudioBlob.size / 1048576).toFixed(1);
      videoPreviewDurationVal.textContent = formatTime(currentAudioDuration);

      youtubeStatusBadge.innerHTML = `
        <div class="mt-2 p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-semibold flex items-center justify-between">
          <span class="flex items-center space-x-2">
            <i data-lucide="check-circle" class="w-4 h-4 text-emerald-400"></i>
            <span>✓ Audio Ready: ${formatTime(currentAudioDuration)} (${mbSize} MB AAC) &bull; Auto-Starting Transcription...</span>
          </span>
          <span class="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300">GPU Ready</span>
        </div>
      `;
      lucide.createIcons();
      showToast(`AAC Audio loaded (${formatTime(currentAudioDuration)})! Starting transcription on your device...`, 'success');

      // Auto-start transcription directly!
      setTimeout(() => {
        startTranscribeBtn.click();
      }, 600);

    } else {
      const displayErr = backendErrorMsg && backendErrorMsg.includes('Sign in to confirm')
        ? 'YouTube blocked the Colab cloud IP ("Sign in to confirm you\'re not a bot"). Run the backend on your own PC or upload cookies.txt to Colab, or use 1-click download below:'
        : (backendErrorMsg ? `Backend error: ${escapeHtml(backendErrorMsg.slice(0, 140))}` : 'Browser CORS Restriction: YouTube blocks direct client streaming without a connected backend.');

      youtubeStatusBadge.innerHTML = `
        <div class="mt-3 p-3.5 rounded-xl bg-slate-900/90 border border-slate-700/80 space-y-3">
          <div class="flex items-center space-x-2 text-amber-400 text-xs font-semibold">
            <i data-lucide="info" class="w-4 h-4 shrink-0"></i>
            <span>${displayErr}</span>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-2.5 pt-1">
            <a href="https://yt5s.biz/en/youtube-to-mp3?q=https://www.youtube.com/watch?v=${videoId}" target="_blank" rel="noopener noreferrer" 
               class="px-3.5 py-2.5 rounded-lg bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-500 hover:to-rose-500 text-white font-bold text-xs flex items-center justify-center space-x-1.5 shadow transition">
              <i data-lucide="download" class="w-4 h-4"></i>
              <span>1. Download Audio (Fast AAC/MP3) ↗</span>
            </a>
            <label class="px-3.5 py-2.5 rounded-lg bg-brand-600 hover:bg-brand-500 text-white font-bold text-xs flex items-center justify-center space-x-1.5 cursor-pointer shadow transition">
              <i data-lucide="upload" class="w-4 h-4"></i>
              <span>2. Drop Audio File (Auto-Transcribes)</span>
              <input type="file" id="ytAudioFileInput" class="hidden" accept="audio/*,video/*,.mp3,.wav,.m4a,.aac">
            </label>
          </div>
          <p class="text-[11px] text-slate-400">
            💡 Once loaded, your device's <strong>GPU (WebGPU)</strong> or <strong>CPU</strong> transcribes the speech with 100% privacy!
          </p>
        </div>
      `;
      lucide.createIcons();

      // Setup drop & select listener on the preview card
      const ytFileInput = document.getElementById('ytAudioFileInput');
      if (ytFileInput) {
        ytFileInput.addEventListener('change', async (e) => {
          if (e.target.files && e.target.files[0]) {
            const file = e.target.files[0];
            await decodeAudioFile(file);
            videoPreviewDurationVal.textContent = formatTime(currentAudioDuration);
            youtubeStatusBadge.innerHTML = `<div class="mt-2 text-xs text-emerald-400 font-semibold flex items-center space-x-1.5"><i data-lucide="check-circle" class="w-4 h-4"></i><span>Audio loaded: ${escapeHtml(file.name)} (${formatTime(currentAudioDuration)})</span> &bull; Starting transcription...</div>`;
            lucide.createIcons();
            showToast('Audio loaded! Starting transcription...', 'success');
            setTimeout(() => { startTranscribeBtn.click(); }, 600);
          }
        });
      }
    }
  } catch (err) {
    if (ytTimerInterval) clearInterval(ytTimerInterval);
    showToast(err.message, 'error');
  } finally {
    fetchInfoBtn.disabled = false;
    fetchInfoBtn.innerHTML = `<i data-lucide="search" class="w-4 h-4"></i><span>Load Video</span>`;
    lucide.createIcons();
  }
}

fetchInfoBtn.addEventListener('click', handleYouTubeUrl);
youtubeUrlInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') handleYouTubeUrl();
});

// Allow drag and drop of audio files directly onto the YouTube preview card
['dragenter', 'dragover'].forEach(name => {
  videoPreviewCard.addEventListener(name, (e) => {
    e.preventDefault();
    videoPreviewCard.classList.add('border-brand-500');
  });
});

['dragleave', 'drop'].forEach(name => {
  videoPreviewCard.addEventListener(name, (e) => {
    e.preventDefault();
    videoPreviewCard.classList.remove('border-brand-500');
  });
});

videoPreviewCard.addEventListener('drop', async (e) => {
  if (e.dataTransfer.files && e.dataTransfer.files[0]) {
    const file = e.dataTransfer.files[0];
    await decodeAudioFile(file);
    videoPreviewDurationVal.textContent = formatTime(currentAudioDuration);
    youtubeStatusBadge.innerHTML = `<div class="mt-2 text-xs text-emerald-400 font-semibold flex items-center space-x-1.5"><i data-lucide="check-circle" class="w-4 h-4"></i><span>Audio loaded: ${escapeHtml(file.name)} (${formatTime(currentAudioDuration)})</span> &bull; Starting transcription...</div>`;
    showToast('Audio loaded! Starting transcription...', 'success');
    lucide.createIcons();
    setTimeout(() => { startTranscribeBtn.click(); }, 600);
  }
});

// 7. Microphone Recording
micRecordBtn.addEventListener('click', async () => {
  if (!isRecordingMic) {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      recordedChunks = [];
      mediaRecorder = new MediaRecorder(stream);

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) recordedChunks.push(e.data);
      };

      mediaRecorder.onstop = async () => {
        const blob = new Blob(recordedChunks, { type: 'audio/webm' });
        currentMediaTitle = `Microphone Recording (${new Date().toLocaleTimeString()})`;
        currentMediaAuthor = "Your Voice";
        await decodeAudioFile(blob);
        micStatusTitle.textContent = `Recorded ${formatTime(currentAudioDuration)} - Ready!`;
        showToast('Microphone recording captured and decoded!', 'success');
      };

      mediaRecorder.start();
      isRecordingMic = true;
      micSeconds = 0;
      micTimer.textContent = "00:00";
      micRecordBtn.classList.replace('bg-red-500', 'bg-amber-500');
      micStatusTitle.textContent = "Recording in progress... Click again to stop";
      micRecordingBadge.classList.remove('hidden');

      micTimerInterval = setInterval(() => {
        micSeconds++;
        micTimer.textContent = formatTime(micSeconds);
      }, 1000);

    } catch (err) {
      showToast('Microphone access denied: ' + err.message, 'error');
    }
  } else {
    // Stop recording
    mediaRecorder.stop();
    mediaRecorder.stream.getTracks().forEach(t => t.stop());
    clearInterval(micTimerInterval);
    isRecordingMic = false;
    micRecordBtn.classList.replace('bg-amber-500', 'bg-red-500');
    micRecordingBadge.classList.add('hidden');
  }
});

// 8. Quick 1-Click Demo Audio
async function loadSampleDemoAudio() {
  try {
    showToast('Loading demo audio sample...', 'success');
    const res = await fetch('./static/sample.mp3');
    if (!res.ok) throw new Error('Could not find sample.mp3');
    const blob = await res.blob();
    currentMediaTitle = "Me at the zoo (First YouTube Video)";
    currentMediaAuthor = "jawed (YouTube History)";
    await decodeAudioFile(blob);

    // Show preview
    videoPreviewThumbnail.src = "https://img.youtube.com/vi/jNQXAC9IVRw/hqdefault.jpg";
    videoPreviewTitle.textContent = currentMediaTitle;
    videoPreviewChannelVal.textContent = currentMediaAuthor;
    videoPreviewDurationVal.textContent = formatTime(currentAudioDuration);
    youtubeStatusBadge.innerHTML = `<span class="text-emerald-400 font-semibold">&check; Demo audio loaded and ready to transcribe!</span>`;
    videoPreviewCard.classList.remove('hidden');

    showToast('Demo audio loaded! Click "Start Transcription".', 'success');
  } catch (err) {
    showToast('Failed to load demo: ' + err.message, 'error');
  }
}

quickDemoBtn.addEventListener('click', loadSampleDemoAudio);

// 9. Web Worker Management & Transcription Execution
function initWorker() {
  if (!activeWorker) {
    activeWorker = new Worker('./static/worker.js', { type: 'module' });
  }
  return activeWorker;
}

startTranscribeBtn.addEventListener('click', async () => {
  if (!currentAudioFloat32 || currentAudioFloat32.length === 0) {
    showToast('Please load audio first via YouTube, File Upload, or 1-Click Demo.', 'error');
    return;
  }

  const modelSize = modelSelect.value;
  const device = deviceSelect.value;
  const language = languageSelect.value;
  const task = taskSelect.value;

  // UI state transition
  startTranscribeBtn.disabled = true;
  progressCard.classList.remove('hidden');
  resultsCard.classList.add('hidden');
  progressBarFill.style.width = '0%';
  progressPctText.textContent = '0%';
  progressStatusText.textContent = 'Initializing in-browser Whisper...';
  progressSubText.textContent = 'Loading ONNX model into client memory (GPU/CPU)...';
  liveStreamTerminal.innerHTML = '<p class="text-slate-500 italic">&gt; Initializing worker and compiling shaders...</p>';

  const worker = initWorker();

  // Progress simulation / tracking
  let lastProgressPct = 5;

  // Live elapsed timer during transcription
  const transcribeStartMs = Date.now();
  const transcribeTimerInterval = setInterval(() => {
    const sec = Math.floor((Date.now() - transcribeStartMs) / 1000);
    const m = Math.floor(sec / 60).toString().padStart(2, '0');
    const s = (sec % 60).toString().padStart(2, '0');
    if (progressStatusText.textContent.includes('Transcribing')) {
      progressPctText.textContent = `${m}:${s}`;
    }
  }, 1000);

  worker.onmessage = (e) => {
    const msg = e.data;

    if (msg.type === 'progress') {
      const p = msg.data;
      if (p.status === 'progress' && p.total) {
        const pct = Math.min(95, Math.round((p.loaded / p.total) * 100));
        progressBarFill.style.width = `${pct}%`;
        progressPctText.textContent = `${pct}%`;
        progressStatusText.textContent = `Loading Whisper AI Model (${p.file || 'weights'})...`;
        progressSubText.textContent = `AI Neural Network: ${(p.loaded / 1024 / 1024).toFixed(1)} MB / ${(p.total / 1024 / 1024).toFixed(1)} MB (GPU Memory)`;
      }
    } else if (msg.type === 'stream_text') {
      progressBarFill.classList.add('animate-pulse');
      progressBarFill.style.width = '90%';
      if (msg.text) {
        appendLiveStreamLine(`&gt; ${escapeHtml(msg.text)}`);
      }
    } else if (msg.type === 'chunk_progress') {
      progressBarFill.classList.remove('animate-pulse');
      progressBarFill.style.width = `${msg.pct}%`;
      progressPctText.textContent = `${msg.pct}%`;
      progressStatusText.textContent = `Transcribing chunk ${msg.completed} of ${msg.total}...`;
      if (msg.text) {
        appendLiveStreamLine(`&gt; [${msg.completed}/${msg.total}] ${escapeHtml(msg.text)}`);
      }
    } else if (msg.type === 'status') {
      progressStatusText.textContent = msg.message;
      if (msg.message.includes('Transcribing')) {
        const audioMB = currentAudioBlob ? (currentAudioBlob.size / 1048576).toFixed(1) : '2.7';
        progressSubText.textContent = `Transcribing Audio: ${audioMB} MB (${formatTime(currentAudioDuration)}) • 100% Private (No Audio Cached)`;
        progressBarFill.style.width = '95%';
        progressBarFill.classList.add('animate-pulse');
        progressPctText.textContent = 'Active';
      }
      if (msg.message.includes('WebGPU Pipeline Ready')) {
        appendLiveStreamLine('&gt; WebGPU Pipeline Ready. Executing on your device GPU!');
      } else if (msg.message.includes('WebAssembly CPU Pipeline Ready')) {
        appendLiveStreamLine('&gt; WebAssembly CPU Pipeline Ready. Multi-threaded WASM active.');
      }
    } else if (msg.type === 'complete') {
      clearInterval(transcribeTimerInterval);
      progressBarFill.classList.remove('animate-pulse');
      progressBarFill.style.width = '100%';
      progressPctText.textContent = '100%';
      progressStatusText.textContent = 'Transcription Complete!';
      progressSubText.textContent = `Finished in ${msg.result.execution_time || ''}s using ${msg.result.device_used}`;

      setTimeout(() => {
        progressCard.classList.add('hidden');
        startTranscribeBtn.disabled = false;

        const resData = {
          id: 'rec_' + Date.now(),
          title: currentMediaTitle,
          uploader: currentMediaAuthor,
          language: language === 'auto' ? 'Auto (Detected)' : language.toUpperCase(),
          duration: currentAudioDuration,
          model_used: `Whisper-${modelSize.toUpperCase()}`,
          device_used: msg.result.device_used,
          full_text: msg.result.full_text,
          segments: msg.result.segments,
          created_at: new Date().toISOString()
        };

        // Generate client-side offline summary
        resData.summary = generateOfflineSummary(resData.full_text, resData.segments);

        // Save to browser history
        saveToHistory(resData);

        // Display results
        displayResults(resData);
      }, 500);

    } else if (msg.type === 'error') {
      clearInterval(transcribeTimerInterval);
      progressCard.classList.add('hidden');
      startTranscribeBtn.disabled = false;
      showToast('Transcription error: ' + msg.error, 'error');
    }
  };

  worker.onerror = (err) => {
    progressCard.classList.add('hidden');
    startTranscribeBtn.disabled = false;
    showToast('Worker error: ' + err.message, 'error');
  };

  // Dispatch transcription request to worker
  worker.postMessage({
    type: 'transcribe',
    data: {
      audio: currentAudioFloat32,
      modelSize: modelSize,
      device: device,
      language: language,
      task: task
    }
  });

  appendLiveStreamLine(`&gt; Audio length: ${formatTime(currentAudioDuration)} (${currentAudioFloat32.length} samples at 16kHz)`);
  appendLiveStreamLine(`&gt; Dispatching to client compute thread...`);
});

function appendLiveStreamLine(html) {
  const placeholder = liveStreamTerminal.querySelector('.italic');
  if (placeholder) placeholder.remove();

  const p = document.createElement('p');
  p.innerHTML = html;
  liveStreamTerminal.appendChild(p);
  liveStreamTerminal.scrollTop = liveStreamTerminal.scrollHeight;
}

// 10. Results Display & Interactive Segments
function displayResults(data) {
  currentRecordId = data.id;
  currentSegments = data.segments || [];
  currentFullText = data.full_text || "";

  resultTitle.textContent = data.title || "Untitled";
  resultAuthor.textContent = data.uploader || "In-Browser";
  resultLangBadge.textContent = data.language;
  resultModelBadge.textContent = `${data.model_used} &bull; ${data.device_used}`;
  resultDurationBadge.textContent = formatTime(data.duration);

  // Render Segments
  renderSegments(currentSegments);

  // Render Continuous Text
  continuousTextContent.textContent = currentFullText;

  // Render AI Summary & Chapters
  renderSummary(data.summary);

  // Show Results Panel
  resultsCard.classList.remove('hidden');
  resultsCard.scrollIntoView({ behavior: 'smooth' });
  lucide.createIcons();
}

function renderSegments(segments) {
  viewContainerSegments.innerHTML = '';
  if (!segments || segments.length === 0) {
    viewContainerSegments.innerHTML = '<p class="text-slate-400 p-4">No speech segments detected.</p>';
    return;
  }

  segments.forEach((seg, idx) => {
    const card = document.createElement('div');
    card.className = 'segment-card p-3 rounded-xl bg-slate-50 dark:bg-surface-850 hover:bg-slate-100 dark:hover:bg-surface-800 cursor-pointer flex items-start space-x-3 text-sm';
    card.dataset.start = seg.start;
    card.dataset.end = seg.end;
    card.id = `seg-${idx}`;

    card.innerHTML = `
      <button class="px-2 py-0.5 rounded bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-400 font-mono text-xs font-semibold shrink-0" title="Click to seek audio">
        ${formatTime(seg.start)}
      </button>
      <div class="flex-1 segment-text text-slate-800 dark:text-slate-200">
        ${escapeHtml(seg.text)}
      </div>
      <button class="copy-seg-btn opacity-0 group-hover:opacity-100 text-slate-400 hover:text-slate-200 p-1 rounded" title="Copy segment">
        <i data-lucide="copy" class="w-3.5 h-3.5"></i>
      </button>
    `;

    card.addEventListener('click', (e) => {
      if (e.target.closest('.copy-seg-btn')) {
        navigator.clipboard.writeText(seg.text);
        showToast('Segment copied!', 'success');
        return;
      }
      audioPlayer.currentTime = seg.start;
      audioPlayer.play();
    });

    viewContainerSegments.appendChild(card);
  });
  lucide.createIcons();
}

// 11. Synchronized Audio Playback Highlighting
audioPlayer.addEventListener('timeupdate', () => {
  const curTime = audioPlayer.currentTime;
  const cards = viewContainerSegments.querySelectorAll('.segment-card');

  cards.forEach(card => {
    const start = parseFloat(card.dataset.start);
    const end = parseFloat(card.dataset.end);
    if (curTime >= start && curTime <= end) {
      if (!card.classList.contains('active-segment')) {
        card.classList.add('active-segment');
        card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
    } else {
      card.classList.remove('active-segment');
    }
  });
});

function setAudioSpeed(speed) {
  audioPlayer.playbackRate = speed;
  document.querySelectorAll('.speed-btn').forEach(btn => {
    btn.classList.toggle('active', btn.textContent.trim() === `${speed}x`);
  });
}

// 12. Results Tab Switching
viewTabSegments.addEventListener('click', () => {
  viewTabSegments.className = "px-3.5 py-1.5 rounded-lg text-sm font-semibold bg-brand-600 text-white flex items-center space-x-1.5 transition";
  viewTabText.className = "px-3.5 py-1.5 rounded-lg text-sm font-semibold text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-surface-800 flex items-center space-x-1.5 transition";
  viewTabSummary.className = "px-3.5 py-1.5 rounded-lg text-sm font-semibold text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-surface-800 flex items-center space-x-1.5 transition";
  viewContainerSegments.classList.remove('hidden');
  viewContainerText.classList.add('hidden');
  viewContainerSummary.classList.add('hidden');
});

viewTabText.addEventListener('click', () => {
  viewTabText.className = "px-3.5 py-1.5 rounded-lg text-sm font-semibold bg-brand-600 text-white flex items-center space-x-1.5 transition";
  viewTabSegments.className = "px-3.5 py-1.5 rounded-lg text-sm font-semibold text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-surface-800 flex items-center space-x-1.5 transition";
  viewTabSummary.className = "px-3.5 py-1.5 rounded-lg text-sm font-semibold text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-surface-800 flex items-center space-x-1.5 transition";
  viewContainerText.classList.remove('hidden');
  viewContainerSegments.classList.add('hidden');
  viewContainerSummary.classList.add('hidden');
});

viewTabSummary.addEventListener('click', () => {
  viewTabSummary.className = "px-3.5 py-1.5 rounded-lg text-sm font-semibold bg-brand-600 text-white flex items-center space-x-1.5 transition";
  viewTabSegments.className = "px-3.5 py-1.5 rounded-lg text-sm font-semibold text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-surface-800 flex items-center space-x-1.5 transition";
  viewTabText.className = "px-3.5 py-1.5 rounded-lg text-sm font-semibold text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-surface-800 flex items-center space-x-1.5 transition";
  viewContainerSummary.classList.remove('hidden');
  viewContainerSegments.classList.add('hidden');
  viewContainerText.classList.add('hidden');
});

// 13. In-Transcript Search
transcriptSearchInput.addEventListener('input', () => {
  const query = transcriptSearchInput.value.trim().toLowerCase();
  const textDivs = viewContainerSegments.querySelectorAll('.segment-text');

  if (!query) {
    searchMatchCount.textContent = '';
    textDivs.forEach((el, idx) => {
      if (currentSegments[idx]) el.innerHTML = escapeHtml(currentSegments[idx].text);
    });
    return;
  }

  let matches = 0;
  textDivs.forEach((el, idx) => {
    if (!currentSegments[idx]) return;
    const rawText = currentSegments[idx].text;
    if (rawText.toLowerCase().includes(query)) {
      matches++;
      const regex = new RegExp(`(${escapeRegExp(query)})`, 'gi');
      el.innerHTML = rawText.replace(regex, '<mark class="search-highlight">$1</mark>');
    } else {
      el.innerHTML = escapeHtml(rawText);
    }
  });

  searchMatchCount.textContent = matches > 0 ? `${matches} match${matches === 1 ? '' : 'es'}` : 'No matches';
});

// 14. Client-Side AI Summary & Chapters
function generateOfflineSummary(text, segments) {
  if (!text || text.length < 10) return "No sufficient speech content to summarize.";

  const words = text.toLowerCase().match(/\b[a-z]{3,}\b/g) || [];
  const stopWords = new Set(["the","and","that","have","for","not","with","you","this","but","his","from","they","say","her","she","will","one","all","would","there","their","what","out","about","who","get","which","when","make","can","like","time","just","him","know","take","people","into","year","your","good","some","could","them","see","other","than","then","now","look","only","come","its","over","think","also","back","after","use","two","how","our","work","first","well","way","even","new","want","because","any","these","give","day","most","us"]);

  const freq = {};
  words.forEach(w => {
    if (!stopWords.has(w)) freq[w] = (freq[w] || 0) + 1;
  });

  const topKeywords = Object.entries(freq)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(e => e[0]);

  // Sentence extraction
  const rawSentences = text.match(/[^.!?]+[.!?]+/g) || [text];
  const scoredSentences = rawSentences.map(s => {
    const sWords = s.toLowerCase().match(/\b[a-z]{3,}\b/g) || [];
    let score = 0;
    sWords.forEach(w => { if (freq[w]) score += freq[w]; });
    return { sentence: s.trim(), score: score / (sWords.length || 1) };
  });

  scoredSentences.sort((a, b) => b.score - a.score);
  const highlights = scoredSentences.slice(0, 3).map(s => s.sentence);

  // Chapters breakdown
  let chaptersMd = "";
  if (segments && segments.length > 0) {
    const chapters = [];
    let curChapterStart = 0;
    let curTexts = [];

    segments.forEach(seg => {
      curTexts.push(seg.text);
      if (seg.end - curChapterStart >= 30) {
        chapters.push({
          time: formatTime(curChapterStart),
          summary: curTexts.join(" ").slice(0, 60) + "..."
        });
        curChapterStart = seg.end;
        curTexts = [];
      }
    });

    if (curTexts.length > 0) {
      chapters.push({
        time: formatTime(curChapterStart),
        summary: curTexts.join(" ").slice(0, 60) + "..."
      });
    }

    chaptersMd = chapters.map(c => `- **\`${c.time}\`** ${c.summary}`).join("\n");
  }

  return `
### Executive Summary
${highlights.map(h => `- ${h}`).join("\n")}

### Key Topics
${topKeywords.map(k => `\`${k}\``).join("  ")}

### Timeline Chapters
${chaptersMd || "- **`00:00`** Full Recording"}
  `.trim();
}

function renderSummary(summaryMd) {
  if (!summaryMd) {
    summaryContent.innerHTML = '<p class="text-slate-400">No summary available.</p>';
    return;
  }
  let html = summaryMd
    .replace(/^### (.*$)/gim, '<h3 class="text-base font-bold text-slate-900 dark:text-white mt-3 mb-1">$1</h3>')
    .replace(/^\- \*\*`([^`]+)`\*\* (.*$)/gim, '<div class="flex items-center space-x-2 my-1"><span class="px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 font-mono text-xs font-semibold">$1</span><span>$2</span></div>')
    .replace(/^\- (.*$)/gim, '<li class="ml-4 list-disc text-slate-700 dark:text-slate-300">$1</li>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/`([^`]+)`/g, '<code class="px-1.5 py-0.5 rounded bg-slate-200 dark:bg-surface-800 font-mono text-xs text-brand-400 mr-1">$1</code>');

  summaryContent.innerHTML = html;
}

// 15. Client-Side Exports (SRT, VTT, TXT, JSON, CSV, Markdown)
exportDropdownBtn.addEventListener('click', (e) => {
  e.stopPropagation();
  exportMenu.classList.toggle('hidden');
});

document.addEventListener('click', () => exportMenu.classList.add('hidden'));

function downloadExport(format) {
  if (!currentSegments || currentSegments.length === 0) {
    showToast('No active transcript to export', 'error');
    return;
  }

  let content = "";
  let mimeType = "text/plain";
  let extension = format;
  const filename = `${sanitizeFilename(currentMediaTitle)}.${extension}`;

  if (format === 'srt') {
    content = currentSegments.map((s, i) => {
      return `${i + 1}\n${formatSrtTime(s.start)} --> ${formatSrtTime(s.end)}\n${s.text}\n`;
    }).join("\n");
  } else if (format === 'vtt') {
    content = "WEBVTT\n\n" + currentSegments.map((s, i) => {
      return `${i + 1}\n${formatVttTime(s.start)} --> ${formatVttTime(s.end)}\n${s.text}\n`;
    }).join("\n");
  } else if (format === 'txt') {
    content = currentSegments.map(s => `[${formatTime(s.start)} - ${formatTime(s.end)}]  ${s.text}`).join("\n");
  } else if (format === 'raw_txt') {
    content = currentFullText;
  } else if (format === 'json') {
    mimeType = "application/json";
    content = JSON.stringify({
      title: currentMediaTitle,
      duration: currentAudioDuration,
      full_text: currentFullText,
      segments: currentSegments
    }, null, 2);
  } else if (format === 'csv') {
    mimeType = "text/csv";
    content = "Start,End,Duration,Text\n" + currentSegments.map(s => {
      return `"${formatTime(s.start)}","${formatTime(s.end)}",${(s.end - s.start).toFixed(2)},"${s.text.replace(/"/g, '""')}"`;
    }).join("\n");
  } else if (format === 'md') {
    mimeType = "text/markdown";
    content = `# Transcript: ${currentMediaTitle}\n\n` +
      `**Duration**: ${formatTime(currentAudioDuration)}  \n` +
      `**Exported**: ${new Date().toLocaleString()}  \n\n` +
      `## Full Transcript\n\n${currentFullText}\n\n` +
      `## Timestamped Segments\n\n` +
      currentSegments.map(s => `- **\`${formatTime(s.start)}\`**: ${s.text}`).join("\n");
  }

  const blob = new Blob([content], { type: mimeType });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);

  exportMenu.classList.add('hidden');
  showToast(`Downloaded ${filename}!`, 'success');
}

copyAllBtn.addEventListener('click', () => {
  if (!currentFullText) return;
  navigator.clipboard.writeText(currentFullText);
  showToast('Full transcript copied to clipboard!', 'success');
});

// 16. Local Storage History Management
function saveToHistory(record) {
  try {
    const list = getHistoryList();
    list.unshift(record);
    if (list.length > 50) list.pop(); // keep last 50
    localStorage.setItem('whisperflow_history', JSON.stringify(list));
    updateHistoryBadge();
  } catch (e) {
    console.warn("Failed to save history:", e);
  }
}

function getHistoryList() {
  try {
    return JSON.parse(localStorage.getItem('whisperflow_history') || '[]');
  } catch (e) {
    return [];
  }
}

function updateHistoryBadge() {
  const list = getHistoryList();
  historyCountBadge.textContent = list.length;
}

openHistoryBtn.addEventListener('click', () => {
  historyDrawerBackdrop.classList.remove('hidden');
  renderHistoryDrawer();
});

closeHistoryBtn.addEventListener('click', () => {
  historyDrawerBackdrop.classList.add('hidden');
});

historyDrawerBackdrop.addEventListener('click', (e) => {
  if (e.target === historyDrawerBackdrop) historyDrawerBackdrop.classList.add('hidden');
});

function renderHistoryDrawer(filter = '') {
  const list = getHistoryList();
  const filtered = filter ? list.filter(item => (item.title + ' ' + item.full_text).toLowerCase().includes(filter.toLowerCase())) : list;

  if (filtered.length === 0) {
    historyListContainer.innerHTML = '<p class="text-slate-400 text-xs p-4 text-center">No transcriptions saved yet.</p>';
    return;
  }

  historyListContainer.innerHTML = filtered.map(item => `
    <div class="p-3 rounded-xl bg-slate-50 dark:bg-surface-850 border border-slate-200 dark:border-slate-800 hover:border-brand-500/50 cursor-pointer transition flex items-center justify-between group" onclick="loadHistoryItem('${item.id}')">
      <div class="flex-1 min-w-0 pr-2">
        <h5 class="text-xs font-semibold text-slate-900 dark:text-white truncate">${escapeHtml(item.title)}</h5>
        <div class="flex items-center space-x-2 text-[10px] text-slate-400 mt-0.5">
          <span>${item.language}</span>
          <span>&bull;</span>
          <span>${formatTime(item.duration)}</span>
          <span>&bull;</span>
          <span>${new Date(item.created_at).toLocaleDateString()}</span>
        </div>
      </div>
      <button onclick="deleteHistoryItem(event, '${item.id}')" class="opacity-0 group-hover:opacity-100 p-1 text-slate-400 hover:text-red-400 transition" title="Delete record">
        <i data-lucide="trash-2" class="w-4 h-4"></i>
      </button>
    </div>
  `).join('');

  lucide.createIcons();
}

window.loadHistoryItem = function(id) {
  const list = getHistoryList();
  const item = list.find(x => x.id === id);
  if (item) {
    historyDrawerBackdrop.classList.add('hidden');
    displayResults(item);
  }
};

window.deleteHistoryItem = function(e, id) {
  e.stopPropagation();
  let list = getHistoryList();
  list = list.filter(x => x.id !== id);
  localStorage.setItem('whisperflow_history', JSON.stringify(list));
  updateHistoryBadge();
  renderHistoryDrawer(historySearchInput.value.trim());
};

historySearchInput.addEventListener('input', () => {
  renderHistoryDrawer(historySearchInput.value.trim());
});

// 17. Utilities & Time Formatters
function formatTime(seconds) {
  if (isNaN(seconds) || seconds < 0) return "00:00";
  const hrs = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  if (hrs > 0) {
    return `${hrs.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

function formatSrtTime(seconds) {
  const hrs = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  const ms = Math.floor((seconds % 1) * 1000);
  return `${hrs.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')},${ms.toString().padStart(3, '0')}`;
}

function formatVttTime(seconds) {
  return formatSrtTime(seconds).replace(',', '.');
}

function escapeHtml(str) {
  return (str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function escapeRegExp(string) {
  return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function sanitizeFilename(name) {
  return (name || 'transcript').replace(/[^a-zA-Z0-9_-]/g, '_').slice(0, 50);
}

function showToast(message, type = 'success') {
  const toast = document.getElementById('toastNotification');
  const msgEl = document.getElementById('toastMessage');
  const icon = document.getElementById('toastIcon');

  msgEl.textContent = message;
  if (type === 'error') {
    toast.className = "fixed bottom-5 right-5 z-50 transform translate-y-0 opacity-100 transition-all duration-300 px-4 py-3 rounded-xl shadow-xl flex items-center space-x-2 text-sm font-medium bg-red-600 text-white";
    icon.setAttribute('data-lucide', 'alert-circle');
  } else {
    toast.className = "fixed bottom-5 right-5 z-50 transform translate-y-0 opacity-100 transition-all duration-300 px-4 py-3 rounded-xl shadow-xl flex items-center space-x-2 text-sm font-medium bg-emerald-600 text-white";
    icon.setAttribute('data-lucide', 'check-circle');
  }
  lucide.createIcons();

  setTimeout(() => {
    toast.classList.add('translate-y-20', 'opacity-0');
  }, 4000);
}

// 18. App Initialization
window.addEventListener('DOMContentLoaded', async () => {
  initTheme();
  updateHistoryBadge();
  await detectHardware();
});
