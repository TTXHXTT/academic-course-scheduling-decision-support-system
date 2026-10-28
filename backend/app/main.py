"""
ACS - Academic Course Scheduling Decision-Support System
Main FastAPI application entry point.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
import os

from app.core.config import settings
from app.core.database import init_db
from app.api import auth, datasets, records, analysis, recommendations, scenarios, audit


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="ACS - Academic Course Scheduling Decision-Support System",
    description="Decision-support system for academic course offering decisions at CSUSB. CSE 6550 project.",
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

static_dir = os.path.join(os.path.dirname(__file__), "static")
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=templates_dir)

app.include_router(auth.router)
app.include_router(datasets.router)
app.include_router(records.router)
app.include_router(analysis.router)
app.include_router(recommendations.router)
app.include_router(scenarios.router)
app.include_router(audit.router)


def _page(request: Request, name: str, **ctx):
    return templates.TemplateResponse(f"{name}.html", {"request": request, **ctx})


@app.get("/", response_class=HTMLResponse)
def root():
    return RedirectResponse(url="/dashboard")

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return _page(request, "login")

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request):
    return _page(request, "dashboard")

@app.get("/imports", response_class=HTMLResponse)
def imports_page(request: Request):
    return _page(request, "imports")

@app.get("/explorer", response_class=HTMLResponse)
def explorer_page(request: Request):
    return _page(request, "explorer")

@app.get("/analysis", response_class=HTMLResponse)
def analysis_page(request: Request):
    return _page(request, "analysis")

@app.get("/recommendations", response_class=HTMLResponse)
def recommendations_page(request: Request):
    return _page(request, "recommendations")

@app.get("/scenarios", response_class=HTMLResponse)
def scenarios_page(request: Request):
    return _page(request, "scenarios")

@app.get("/history", response_class=HTMLResponse)
def history_page(request: Request):
    return _page(request, "history")

@app.get("/audit", response_class=HTMLResponse)
def audit_page(request: Request):
    return _page(request, "audit")

@app.get("/health")
def health():
    return {"status": "healthy", "version": settings.APP_VERSION}
