from fastapi import FastAPI
from backend.core.routing import MultimodalRouter
from backend.core.admin import AdminManager
from backend.core.bootstrapper import Bootstrapper
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import Optional
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

router = MultimodalRouter()
admin = AdminManager()

frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
app.mount("/static", StaticFiles(directory=frontend_path), name="static")

@app.on_event("startup")
async def startup_event():
    Bootstrapper().run()

@app.get("/")
async def read_index():
    from fastapi.responses import FileResponse
    return FileResponse(os.path.join(frontend_path, "index.html"))

class RouteRequest(BaseModel):
    start_lat: float
    start_lon: float
    end_lat: float
    end_lon: float
    mode: Optional[str] = 'transit'

@app.post("/route")
async def find_route(req: RouteRequest):
    path = router.find_path(req.start_lat, req.start_lon, req.end_lat, req.end_lon, mode=req.mode)
    return {"path": path}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/bounds")
async def get_bounds():
    bounds = router.get_graph_bounds()
    return {"bounds": bounds}

@app.get("/stations")
async def get_stations():
    return {"stations": router.get_all_stations()}

@app.get("/evs")
async def get_evs():
    return {"evs": router.get_all_evs()}
