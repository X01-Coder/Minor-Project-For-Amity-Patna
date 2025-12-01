"""Minimal test endpoint for Vercel."""
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Minimal FastAPI works on Vercel"}

@app.get("/health")
def health():
    return {"status": "healthy"}
