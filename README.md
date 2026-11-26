# 🎙️ Free Online YouTube Transcriber & Audio-to-Text Converter (URLs, MP3, WAV, MP4)

[![MiniMaxTools](https://img.shields.io/badge/Featured%20Partner-MiniMaxTools.com-ff5722?style=for-the-badge&logo=google-chrome)](https://tinyurl.com/4xtf9sye)
[![GitHub Pages](https://img.shields.io/badge/Live%20App-Free%20Online%20YouTube%20Transcriber-6366f1?style=for-the-badge&logo=github)](https://umeshkumar20540-oss.github.io/free-online-youtube-transcriber-audio-to-text-converter/)
[![WebGPU](https://img.shields.io/badge/Hardware-WebGPU%20%2B%20WASM-10b981?style=for-the-badge&logo=webassembly)](https://umeshkumar20540-oss.github.io/free-online-youtube-transcriber-audio-to-text-converter/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

> 🌟 **Discover 100+ Free Online AI Tools**: Visit **[MiniMaxTools.com](https://tinyurl.com/4xtf9sye)** for free AI media converters, productivity web apps, and utilities!
>
> **🚀 Live Web App**: [https://umeshkumar20540-oss.github.io/free-online-youtube-transcriber-audio-to-text-converter/](https://umeshkumar20540-oss.github.io/free-online-youtube-transcriber-audio-to-text-converter/)

**Free Online YouTube Transcriber & Audio-to-Text Converter** is a free, unlimited, privacy-first web and desktop application for converting **YouTube URLs, YouTube Shorts, video links, and audio/video files (MP3, WAV, M4A, AAC, MP4, WebM, FLAC)** to text & subtitles **100% directly on your own GPU and CPU** using **Whisper AI**, **Transformers.js (WebGPU/WASM)**, and **Faster-Whisper**.

Audio and speech data **never leave your device** for transcription. Supports **48+ languages** including English, Hindi, Urdu, Bengali, Tamil, Telugu, Marathi, Gujarati, Arabic, Spanish, French, German, Japanese, Korean, and Chinese.

---

## ⚡ Highlights & Key Capabilities

- **YouTube URL & Audio Link Ingestion**:
  - Transcribe YouTube videos, YouTube Shorts, and online media URLs.
  - Automatic thumbnail, title, and channel metadata preview.
- **Upload Any Audio or Video File (MP3, WAV, M4A, MP4, WebM, FLAC)**:
  - Drag-and-drop or select any file format. Client-side decoding via Web Audio API.
- **Client GPU & CPU Acceleration**:
  - **WebGPU**: Automatically utilizes physical NVIDIA, AMD, Intel, or Apple Silicon GPUs for fast parallel inference.
  - **WebAssembly (WASM SIMD)**: Multi-threaded CPU fallback for universal browser compatibility.
- **100% Private (Zero Data Uploads)**:
  - Inference executes entirely in your browser's local memory. Your audio never touches third-party servers.
- **Live Recognition Terminal**:
  - Real-time display of decoded speech segments streaming onto a terminal console as your hardware processes audio.
- **Synchronized Karaoke Player**:
  - Click any segment or timestamp to seek playback to that exact second.
  - Dynamic karaoke highlighting automatically illuminates the active sentence as audio plays.
  - Adjustable playback speed (1x, 1.25x, 1.5x, 2x).
- **Client-Side AI Summary & Chapters**:
  - Offline TF-IDF extractive summarization generates executive bullet points, key topics, and timestamped chapter markers without cloud APIs.
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
👉 **[https://umeshkumar20540-oss.github.io/free-online-youtube-transcriber-audio-to-text-converter/](https://umeshkumar20540-oss.github.io/free-online-youtube-transcriber-audio-to-text-converter/)**

1. Paste a **YouTube URL / Shorts**, drop an **MP3 / WAV / M4A / MP4 file**, or click **"1-Click Test Demo"**.
2. Listen to the **Audio Preview** to verify your audio, and pick your **Language** (48+ languages including English, Hindi, Spanish, Arabic, etc.) and **Whisper Model** (`Tiny`, `Base`, or `Small`).
3. Click **"Start Transcription"**.
4. Your device's GPU (via WebGPU) or CPU (via WASM) transcribes the speech locally with live streaming text!

---

## 💻 Download & Run Offline on Your PC (Windows / Mac / Linux)

Run the full desktop/local version on your own PC with **no external backend**:

### 1. Requirements
- Python 3.10+
- NVIDIA GPU with CUDA (optional, automatic CPU fallback)

### 2. Installation
```bash
git clone https://github.com/umeshkumar20540-oss/free-online-youtube-transcriber-audio-to-text-converter.git
cd free-online-youtube-transcriber-audio-to-text-converter
pip install -r requirements.txt
```

### 3. Launch Local App (1-Click on Windows)
- **Windows:** Double-click `run.bat`
- **Mac / Linux / Terminal:**
  ```bash
  python main.py
  ```
Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser. Everything (YouTube audio download + AI transcription) runs 100% locally on your own PC!

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
├── index.html                # GitHub Pages static entrypoint (SEO optimized)
├── static/
│   ├── app.js               # Client controller (WebGPU detection, UI, export, history)
│   ├── worker.js            # Transformers.js in-browser WebGPU/WASM Whisper worker
│   ├── styles.css           # Custom styling, karaoke highlights, scrollbars
│   └── sample.mp3           # Sample audio for instant 1-click test
├── templates/
│   └── index.html           # FastAPI template mirror
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

## 🌟 Discover 100+ More Free AI & Productivity Tools

Looking for more free web applications, media tools, and AI utilities?
👉 **Check out [MiniMaxTools.com](https://tinyurl.com/4xtf9sye)** for 100+ free online tools, converters, and generators!

---

## 📄 License
Distributed under the MIT License. Whisper models are distributed under OpenAI's MIT weights license.
