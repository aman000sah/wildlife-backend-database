from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import Base, engine

# Import all models first so SQLAlchemy registers them before create_all
import app.models.user          # noqa: F401
import app.models.report        # noqa: F401
import app.models.alert         # noqa: F401
import app.models.ml_detection  # noqa: F401

from app.routes import auth, reports, alerts, heatmap, admin, detect, stats  # single clean import

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Wildlife Sighting & Conflict Prevention API",
    description="Backend for Wild Sentinel mobile app",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,    prefix="/api/auth",    tags=["Authentication"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
app.include_router(alerts.router,  prefix="/api/alerts",  tags=["Alerts"])
app.include_router(heatmap.router, prefix="/api/heatmap", tags=["Heatmap"])
app.include_router(admin.router,   prefix="/api/admin",   tags=["Admin"])
app.include_router(detect.router,  prefix="/api/detect",  tags=["Detection"])
app.include_router(stats.router,   prefix="/api/stats",   tags=["Stats"])

@app.get("/")
def root():
    return {"message": "Wildlife API is running 🐾"}
