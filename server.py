#!/usr/bin/env python3
"""
ALIOS ONE Chat — Community Edition server
=========================================
A tiny local server that:
  1. Serves the app (index.html)
  2. Proxies chat requests to OpenRouter — YOUR API KEY NEVER
     TOUCHES THE BROWSER. It lives in openrouter.key on disk.
  3. Persists your chats & memory cards locally (state.json)

No cloud. No accounts. No telemetry. Your conversations stay
on your machine.

Run:  python server.py   →  open http://localhost:8801
"""
import os
import json
import shutil
import tempfile
from pathlib import Path
from datetime import datetime

import requests
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
import uvicorn

# ---------------- config ----------------
HERE = Path(__file__).parent
PORT = 8801
HOST = "127.0.0.1"   # localhost only. Change to "0.0.0.0" to allow
                     # other devices on your network (understand the
                     # risks first — anyone on your network could chat
                     # on your API credit).
KEY_FILE = HERE / "openrouter.key"
STATE_FILE = HERE / "state.json"
BACKUP_DIR = HERE / "backups"

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
ALLOWED_FIELDS = {
    "model", "messages", "stream", "temperature", "top_p", "top_k",
    "frequency_penalty", "presence_penalty", "repetition_penalty",
    "min_p", "max_tokens", "provider",
}


def load_key():
    if not KEY_FILE.exists():
        raise SystemExit(
            "\n❌ No API key found.\n"
            f"   Create a file named 'openrouter.key' next to server.py\n"
            f"   containing your OpenRouter API key (get one free at\n"
            f"   https://openrouter.ai/keys).\n"
            f"   The install script normally does this for you.\n")
    return KEY_FILE.read_text().strip()


API_KEY = load_key()
BACKUP_DIR.mkdir(exist_ok=True)

app = FastAPI(title="ALIOS ONE Chat", version="1.1.0")


# ---------------- chat proxy ----------------
@app.post("/chat")
async def chat_proxy(request: Request):
    body = await request.json()
    if "model" not in body or "messages" not in body:
        raise HTTPException(status_code=422, detail="model and messages required")
    payload = {k: v for k, v in body.items() if k in ALLOWED_FIELDS}
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://aliosone.one",
        "X-Title": "ALIOS ONE Chat",
    }
    if payload.get("stream"):
        def gen():
            try:
                with requests.post(OPENROUTER_URL, headers=headers,
                                   json=payload, stream=True, timeout=300) as r:
                    if r.status_code != 200:
                        err = json.dumps({"error": {"message":
                            f"OpenRouter {r.status_code}: {r.text[:200]}"}})
                        yield f"data: {err}\n\n".encode()
                        return
                    for chunk in r.iter_content(chunk_size=None):
                        if chunk:
                            yield chunk
            except Exception as e:
                yield f"data: {json.dumps({'error': {'message': str(e)}})}\n\n".encode()
        return StreamingResponse(gen(), media_type="text/event-stream")
    r = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=300)
    if r.status_code != 200:
        raise HTTPException(status_code=502,
                            detail=f"OpenRouter {r.status_code}: {r.text[:200]}")
    return r.json()


# ---------------- state (chats + memory cards) ----------------
def atomic_write(path: Path, data: dict):
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        os.replace(tmp, str(path))
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


@app.post("/state/save")
async def save_state(request: Request):
    data = await request.json()
    chats = data.get("chats")
    if not isinstance(chats, list) or any(
            not isinstance(c, dict) or "id" not in c for c in chats):
        raise HTTPException(status_code=422, detail="invalid state structure")

    # deleted-chat tombstones: union server+client, then filter
    existing = {}
    if STATE_FILE.exists():
        try:
            existing = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            existing = {}
    tombs = set(existing.get("deletedChatIds", []) or []) | \
            set(data.get("deletedChatIds", []) or [])
    data["deletedChatIds"] = sorted(tombs)[-500:]
    data["chats"] = [c for c in chats if c["id"] not in tombs]

    if STATE_FILE.exists():
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(STATE_FILE, BACKUP_DIR / f"state_{stamp}.json")
        for old in sorted(BACKUP_DIR.glob("state_*.json"), reverse=True)[5:]:
            old.unlink()

    atomic_write(STATE_FILE, data)
    return {"status": "ok", "chats": len(data["chats"])}


@app.get("/state/load")
def load_state():
    if not STATE_FILE.exists():
        return {"status": "empty", "data": None}
    return {"status": "ok",
            "data": json.loads(STATE_FILE.read_text(encoding="utf-8"))}


@app.get("/health")
def health():
    return {"status": "ok", "app": "ALIOS ONE Chat CE", "version": "1.1.0"}


@app.get("/", response_class=HTMLResponse)
def serve_app():
    idx = HERE / "index.html"
    if not idx.exists():
        return HTMLResponse("<h1>ALIOS ONE Chat</h1><p>index.html missing "
                            "next to server.py</p>", status_code=404)
    return HTMLResponse(idx.read_text(encoding="utf-8"),
                        headers={"Cache-Control": "no-store"})


if __name__ == "__main__":
    print("=" * 56)
    print("  ALIOS ONE Chat — Community Edition")
    print(f"  Open:  http://localhost:{PORT}")
    print("  Your API key stays on this machine. Always.")
    print("=" * 56)
    uvicorn.run(app, host=HOST, port=PORT)
