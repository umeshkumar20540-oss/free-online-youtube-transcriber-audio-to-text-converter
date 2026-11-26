# 🎙️ WhisperFlow: In-Browser AI YouTube & Audio Transcriber

[![GitHub Pages](https://img.shields.io/badge/Live%20Demo-GitHub%20Pages-6366f1?style=for-the-badge&logo=github)](https://umeshkumar20540-oss.github.io/youtube-transcriber/)
[![WebGPU](https://img.shields.io/badge/Hardware-WebGPU%20%2B%20WASM-10b981?style=for-the-badge&logo=webassembly)](https://umeshkumar20540-oss.github.io/youtube-transcriber/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

> **🚀 Live Web App**: [https://umeshkumar20540-oss.github.io/youtube-transcriber/](https://umeshkumar20540-oss.github.io/youtube-transcriber/)

**WhisperFlow** is a modern, high-performance speech transcription application that runs **100% directly in your browser on your own GPU and CPU** using **Transformers.js (ONNX Runtime Web)** and **WebGPU**. 

Audio and speech data **never leave your device**. No servers, no API keys, and no subscription fees required.

---

## ⚡ Highlights & Key Capabilities

- **Client GPU & CPU Acceleration**:
  - **WebGPU**: Automatically utilizes your physical NVIDIA, AMD, Intel, or Apple Silicon GPU for fast parallel inference.
  - **WebAssembly (WASM SIMD)**: Multi-threaded CPU fallback ensuring compatibility across every modern browser.
- **Privacy First (Zero Server Data Transfer)**:
  - Speech decoding and audio transformations happen in client-side memory using the Web Audio API and Web Workers.
- **Multiple Audio Sources**:
  - **YouTube URL**: Instant metadata preview, thumbnail extraction, and audio stream resolution.
  - **Local Audio/Video Upload**: Drag & drop MP3, WAV, M4A, AAC, MP4, WebM, FLAC, and OGG.
  - **Live Microphone Recording**: Record spoken audio directly from your microphone with live waveform tracking.
  - **1-Click Test Demo**: Pre-bundled sample audio to test transcription speed with zero setup.
- **Live Recognition Terminal**:
  - Real-time display of decoded segments streaming onto a terminal console as your hardware processes speech.
- **Synchronized Karaoke Player**:
  - Click any segment or timestamp to seek playback to that exact second.
  - Dynamic karaoke highlighting automatically illuminates the active sentence as audio plays.
  - Adjustable playback speed (1x, 1.25x, 1.5x, 2x).
- **Client-Side AI Summary & Chapters**:
  - Offline TF-IDF extractive summarization generates executive bullet points, top keywords, and timestamped chapter markers without cloud APIs.
- **Multi-Format Subtitle & Text Exports**:
  - **SRT** (`.srt` SubRip Subtitles for Premiere Pro, DaVinci Resolve, VLC)
  - **WebVTT** (`.vtt` for HTML5 video)
  - **Timestamped Text** (`.txt`)
  - **Plain Text** (`.txt` clean paragraphs)
  - **JSON** (`.json` with segment timestamps)
  - **Spreadsheet** (`.csv`)
  - **Markdown** (`.md` formatted report with headings)
- **Local History Archive**:
  - Persistent browser storage (`localStorage`) to search, review, and re-export past transcriptions anytime.

---

## 🌐 Run Online (GitHub Pages)

Open the live URL in any modern browser (Chrome, Edge, Brave, Arc, Safari, Firefox):
👉 **[https://umeshkumar20540-oss.github.io/youtube-transcriber/](https://umeshkumar20540-oss.github.io/youtube-transcriber/)**

1. Click **"1-Click Test Demo"** or upload an audio file / paste a YouTube link.
2. Select your desired Whisper model (`Tiny`, `Base`, or `Small`).
3. Click **"Start Transcription"**.
4. Your device's GPU (via WebGPU) or CPU (via WASM) will transcribe the speech locally in seconds!

---

## 💻 Optional: Local Python Server & CLI

You can also run WhisperFlow as a local desktop backend using **Faster-Whisper (CTranslate2)**:

### 1. Requirements
- Python 3.9+
- NVIDIA GPU with CUDA (optional, automatic CPU fallback)

### 2. Installation
```bash
git clone https://github.com/umeshkumar20540-oss/youtube-transcriber.git
cd youtube-transcriber
pip install -r requirements.txt
```

### 3. Launch Local Server
```bash
python main.py
```
Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

### 4. Standalone CLI Usage
```bash
# Transcribe YouTube video to SRT
python cli.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --format srt

# Transcribe local audio file
python cli.py "sample.mp3" --model small --format all --output-dir ./transcripts
```

---

## 🛠️ Project Structure

```
youtube-transcriber/
├── index.html                # GitHub Pages static entrypoint
├── static/
│   ├── app.js               # Client controller (WebGPU detection, UI, export, history)
│   ├── worker.js            # Transformers.js in-browser WebGPU/WASM Whisper worker
│   ├── styles.css           # Custom styling, karaoke highlights, scrollbars
│   └── sample.mp3           # Sample audio for instant 1-click test
├── .github/workflows/
│   └── deploy-pages.yml     # Automated GitHub Pages CI/CD workflow
├── main.py                  # Optional: FastAPI local backend server
├── cli.py                   # Optional: Python Command-Line Interface
├── transcriber.py           # Optional: Faster-Whisper local engine
├── downloader.py            # Optional: yt-dlp downloader
├── storage.py               # Optional: SQLite local history
├── summarizer.py            # Optional: Python offline summarizer
├── requirements.txt         # Optional: Python dependencies
├── run.bat                  # 1-click Windows launcher
└── run.ps1                  # PowerShell launcher
```

---

## 📄 License
Distributed under the MIT License. Whisper models are distributed under OpenAI's MIT weights license.
