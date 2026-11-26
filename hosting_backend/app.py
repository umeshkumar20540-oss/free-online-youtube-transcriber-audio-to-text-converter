import os
import glob
import tempfile
from urllib.parse import quote
import yt_dlp
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI(title="Online YouTube Transcriber Audio Backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class VideoReq(BaseModel):
    url: str


@app.get("/")
def home():
    has_cookies = os.path.exists(os.path.join(os.path.dirname(__file__), "cookies.txt"))
    return {"status": "Audio Backend Active", "ready": True, "cookies_loaded": has_cookies}


@app.post("/api/audio")
def get_audio(req: VideoReq):
    try:
        out_dir = tempfile.mkdtemp()
        ydl_opts = {
            "format": "ba[abr<=64][ext=m4a]/139/ba[ext=m4a]/140/ba/b",
            "outtmpl": os.path.join(out_dir, "%(id)s.%(ext)s"),
            "concurrent_fragment_downloads": 8,
            "resize_buffer": True,
            "noplaylist": True,
            "extractor_args": {"youtube": {"player_client": ["tv", "ios", "android_vr"]}},
            "quiet": True,
            "no_warnings": True,
        }

        # Automatically use cookies.txt if uploaded next to app.py (needed on datacenter IPs)
        local_cookies = os.path.join(os.path.dirname(__file__), "cookies.txt")
        if os.path.exists(local_cookies):
            ydl_opts["cookiefile"] = local_cookies
        elif os.path.exists("/content/cookies.txt"):
            ydl_opts["cookiefile"] = "/content/cookies.txt"

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(req.url, download=True)
            duration = info.get("duration", 0)
            title = quote(str(info.get("title", "audio"))[:100])
            uploader = quote(str(info.get("uploader", ""))[:100])

        files = glob.glob(os.path.join(out_dir, "*.*"))
        if not files:
            raise HTTPException(status_code=500, detail="Audio extraction failed")

        file_path = files[0]
        ext = os.path.splitext(file_path)[1].lower()
        media_type = "audio/mp4" if ext in [".m4a", ".mp4", ".aac"] else "audio/mpeg"

        return FileResponse(
            file_path,
            media_type=media_type,
            filename=os.path.basename(file_path),
            headers={
                "X-Audio-Duration": str(duration),
                "X-Audio-Title": title,
                "X-Audio-Uploader": uploader,
                "Access-Control-Expose-Headers": "X-Audio-Duration, X-Audio-Title, X-Audio-Uploader, Content-Length",
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
