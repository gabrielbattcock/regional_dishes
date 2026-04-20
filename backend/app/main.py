from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

from app.api.routes import recipes, regions

load_dotenv()

app = FastAPI(
    title="Regional Dishes API",
    description="API serving regional recipe data for the interactive map",
    version="0.1.0",
)

# CORS — allow the React dev server
origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(recipes.router, prefix="/api/recipes", tags=["recipes"])
app.include_router(regions.router, prefix="/api/regions", tags=["regions"])


@app.get("/")
def health_check():
    return {"status": "ok", "message": "Regional Dishes API is running"}
