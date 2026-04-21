from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import Base, engine
from app.routes import auth, reports, alerts, device_tokens
import app.models
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Wildlife Sighting & Conflict Prevention API",
    description="Backend for Wildlife Safety Mobile App",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["Alerts"])
app.include_router(device_tokens.router, prefix="/api/devices", tags=["Device Tokens"])

@app.get("/")
def root():
    return {"message": "Wildlife Safety API is running 🐾"}