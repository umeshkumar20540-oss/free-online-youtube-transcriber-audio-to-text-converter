# Hosting Server Deployment Guide

Upload the files in this folder (`app.py`, `requirements.txt`, `Procfile`) to your hosting server (VPS, Render, Koyeb, Railway, or Python hosting).

## 1. Install & Run
```bash
pip install -r requirements.txt
python app.py
```
Or with Uvicorn:
```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

## 2. Important: If YouTube Blocks Your Server IP
If your hosting server uses a datacenter IP and YouTube returns `"Sign in to confirm you're not a bot"`, export your YouTube cookies from your browser (using a "Get cookies.txt LOCALLY" extension) and upload `cookies.txt` into the same folder as `app.py`. The server will automatically detect and use it.

## 3. Connect to Your GitHub Pages Site
1. Open https://umeshkumar20540-oss.github.io/youtube-transcriber/
2. Click the green **Server** icon in the top-right bar.
3. Paste your hosting server's HTTPS URL (for example: `https://api.yourdomain.com`).
