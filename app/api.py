from app.main import app, queue


@app.get("/health")
async def health_check():
    return {"status": "online", "items_in_queue": queue.qsize()}
