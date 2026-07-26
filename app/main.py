"""
REST API for the URL shortener, built with FastAPI.

Endpoints:
    POST /shorten      { "url": "https://example.com" } -> { "short_code": "..." }
    GET  /{short_code}  -> 307 redirect to the original URL
    GET  /health        -> service health check
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, HttpUrl

from app.shortener import URLShortener
from app.storage import SQLiteStorage

app = FastAPI(title="URL Shortener API", version="1.0.0")

storage = SQLiteStorage()
shortener = URLShortener(storage)


class ShortenRequest(BaseModel):
    url: HttpUrl


class ShortenResponse(BaseModel):
    short_code: str
    original_url: str


@app.post("/shorten", response_model=ShortenResponse)
def shorten_url(request: ShortenRequest) -> ShortenResponse:
    code = shortener.shorten(str(request.url))
    return ShortenResponse(short_code=code, original_url=str(request.url))


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok", "stored_urls": storage.count()}


# Registered last: FastAPI matches routes in registration order, and
# this catch-all would otherwise shadow any route defined below it
# (like /health), swallowing those paths as if they were short codes.
@app.get("/{short_code}")
def redirect_to_original(short_code: str) -> RedirectResponse:
    original_url = shortener.resolve(short_code)
    if original_url is None:
        raise HTTPException(status_code=404, detail="Short code not found")
    return RedirectResponse(url=original_url, status_code=307)
