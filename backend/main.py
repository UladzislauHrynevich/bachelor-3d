from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.routers.projects import router as projects_router
from backend.routers.processing import router as processing_router
from backend.routers.videos import router as videos_router

app = FastAPI()

app.include_router(projects_router)
app.include_router(processing_router)

app = FastAPI()

app.include_router(projects_router)

app.include_router(processing_router)
app.include_router(videos_router)
app.mount("/ui", StaticFiles(directory="frontend", html=True))
