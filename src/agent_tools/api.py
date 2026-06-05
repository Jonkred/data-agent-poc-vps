from fastapi import FastAPI

app = FastAPI(title="POC Data Agent Tools API", version="0.1.0")


@app.get("/health")
def health():
    return {"status": "ok", "service": "poc-fastapi"}
