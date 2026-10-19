from fastapi import FastAPI

from backend.routers.projects import router as projects_router
from backend.routers.processing import router as processing_router

app = FastAPI()

app.include_router(projects_router)
app.include_router(processing_router)

app = FastAPI()

app.include_router(projects_router)

app.include_router(processing_router)
