"""HTTP/WebSocket transport for the local evaluation UI."""

import asyncio
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .state import PerturbSequenceError, ProtocolError


def _set_ui_cache_header(path: str, response):
    if path == "/" or path.startswith(("/assets/", "/wasm/")):
        response.headers["Cache-Control"] = "no-store"
    return response


def build_app(session) -> FastAPI:
    static = Path(__file__).with_name("static")
    wasm = Path(__file__).with_name("frontend") / "dist"
    app = FastAPI(title="PredActor conditional eval", docs_url=None, redoc_url=None)
    app.mount("/assets", StaticFiles(directory=static), name="assets")
    app.mount("/wasm", StaticFiles(directory=wasm, check_dir=False), name="wasm")

    @app.middleware("http")
    async def disable_ui_asset_cache(request, call_next):
        response = await call_next(request)
        return _set_ui_cache_header(request.url.path, response)

    @app.get("/")
    def index(): return FileResponse(static / "index.html")

    @app.get("/api/state")
    def state(): return session.state.snapshot()

    @app.get("/api/model/manifest")
    def manifest():
        if session.model_manifest is None:
            raise HTTPException(status_code=503, detail="model is still loading")
        return session.model_manifest

    @app.get("/api/model/{asset_path:path}")
    def model_asset(asset_path: str):
        path = session.model_files.get(asset_path)
        if path is None:
            raise HTTPException(status_code=404, detail="unknown model asset")
        return FileResponse(path, headers={"Cache-Control": "no-store"})

    @app.post("/api/command")
    async def command(payload: dict):
        try:
            return session.state.apply(payload, session)
        except PerturbSequenceError as exc:
            raise HTTPException(status_code=409, detail={
                "code": "stale_perturb_sequence",
                "current_sequence": exc.current_sequence,
                "expected_sequence": exc.current_sequence + 1,
            }) from exc
        except ProtocolError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail={
                'code': 'command_failed', 'message': str(exc),
            }) from exc

    @app.websocket("/ws")
    async def websocket(websocket: WebSocket):
        await websocket.accept()
        try:
            while True:
                await websocket.send_json(session.state.snapshot())
                await asyncio.sleep(0.05)
        except (WebSocketDisconnect, RuntimeError):
            return

    @app.websocket("/ws/sim")
    async def simulation(websocket: WebSocket):
        await websocket.accept()
        try:
            while session.model_manifest is None:
                await asyncio.sleep(0.02)
            handshake = dict(session.model_manifest)
            handshake["perturb"] = dict(handshake.get("perturb", {}),
                                         accepted_sequence=session.perturb_sequence())
            await websocket.send_json(handshake)
            ready = await websocket.receive_json()
            if (ready.get("protocol") != 1 or ready.get("kind") != "ready" or
                    ready.get("model_sha256") != handshake["model_sha256"]):
                await websocket.close(code=1008, reason="invalid client handshake")
                return
            sent = 0
            while True:
                seq, packet = session.snapshot_packet()
                if packet and seq != sent:
                    await websocket.send_bytes(packet)
                    sent = seq
                await asyncio.sleep(0.002)
        except (WebSocketDisconnect, RuntimeError):
            return
        finally:
            session.clear_perturb()
    return app
