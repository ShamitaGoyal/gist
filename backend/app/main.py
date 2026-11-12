from fastapi import FastAPI

app = FastAPI(title="Gist API")

@app.get("/")
async def root():
    return {"message": "Gist API is running!"}

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "application": "Gist"
    }