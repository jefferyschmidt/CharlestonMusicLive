from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI(title="MusicLive Collector API")

@app.get("/", response_class=HTMLResponse)
def root():
    return "<h1>MusicLive Collector API</h1><p>Status: OK</p>"
