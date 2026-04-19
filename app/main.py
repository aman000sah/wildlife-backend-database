from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import Base, engine
from app.routes import auth, reports, alerts, heatmap
import app.models

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Wildlife Sighting & Conflict Prevention API",
    description="Backend for Wild's & Safety mobile app",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["Alerts"])
app.include_router(heatmap.router, prefix="/api/heatmap", tags=["Heatmap"])

@app.get("/")
def root():
    return {"message": "Wildlife API is running 🐾"}