from __future__ import annotations

"""Application bootstrap for the SDV prototype.

This module starts the FastAPI service, exposes the static frontend, and runs a
background simulation loop that continuously advances the vehicle model and
broadcasts the latest state to connected dashboard clients.
"""

import asyncio
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.api.routes import engine, manager, router

app = FastAPI(title="SDV EV Prototype", version="1.0.0")
app.include_router(router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

frontend_dir = Path(__file__).resolve().parent.parent / "frontend"


@app.get("/")
async def index():
    """Serve the dashboard entry page for the local prototype.

    The frontend is a simple static web app and is served as the root document.
    """
    return FileResponse(frontend_dir / "index.html")


app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")


async def background_simulation_loop():
    """Advance the simulation at a fixed timestep while the vehicle is running.

    The loop keeps the EV state fresh for the dashboard and provides the live
    model updates that appear in the browser without requiring a full page reload.
    """
    while True:
        if engine.running:
            engine.tick(dt=0.1)
            await manager.broadcast(engine.get_state())
        await asyncio.sleep(0.1)


@app.on_event("startup")
async def startup_event():
    """Begin the background simulation thread when the FastAPI app boots."""
    asyncio.create_task(background_simulation_loop())


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=False)
