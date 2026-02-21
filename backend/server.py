import asyncio
import json

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from downloader import create_task, get_task
from config import HOST, PORT, DOWNLOAD_DIR


class DownloadRequest(BaseModel):
    url: str
    quality: str = "best"


app = FastAPI(title="VidTool Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "download_dir": DOWNLOAD_DIR}


@app.post("/download")
def download(req: DownloadRequest):
    if not req.url or not req.url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="Invalid URL")
    task_id = create_task(req.url, req.quality)
    return {"task_id": task_id, "status": "queued"}


@app.get("/progress/{task_id}")
async def progress(task_id: str):
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    async def event_stream():
        try:
            while True:
                t = get_task(task_id)
                if not t:
                    break
                yield "data: " + json.dumps(t) + "\n\n"
                if t["status"] in ("finished", "error"):
                    break
                await asyncio.sleep(0.5)
        except (ConnectionResetError, BrokenPipeError, OSError):
            return

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


if __name__ == "__main__":
    import uvicorn
    print("VidTool backend starting on http://{}:{}".format(HOST, PORT))
    print("Downloads will be saved to: {}".format(DOWNLOAD_DIR))
    uvicorn.run(app, host=HOST, port=PORT)
