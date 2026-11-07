import json
import os
import threading
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse

from app import llm
from app.loop import GOAL, tune

ROOT = Path(__file__).resolve().parent.parent
app = FastAPI(title="Robot Control Tuner")
run_lock = threading.Lock()  # one run at a time: protects the server and the LLM quota


def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def mode() -> str:
    llm.load_env()
    mock = os.environ.get("MOCK_LLM") == "1" or not os.environ.get("LLM_API_KEY")
    return "mock" if mock else "live"


@app.get("/")
def index():
    return FileResponse(ROOT / "static" / "index.html")


@app.get("/api/run")
def run():
    def stream():
        if not run_lock.acquire(blocking=False):
            yield sse("busy", {"message": "Another run is in progress. Try again in a minute."})
            return
        try:
            yield sse("start", {"goal": GOAL, "mode": mode()})
            for attempt in tune():
                yield sse("attempt", attempt)
            yield sse("done", {})
        except Exception as e:
            yield sse("failed", {"message": f"{type(e).__name__}: {str(e)[:150]}"})
        finally:
            run_lock.release()

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})