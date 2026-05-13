"""Entrypoint — wire everything."""
from fastapi import FastAPI
from .presentation.controllers.order_controller import router as order_router
from .presentation.middleware.security_headers import SecurityHeadersMiddleware

app = FastAPI(title="Czanix API", version="1.0.0")

app.add_middleware(SecurityHeadersMiddleware)
app.include_router(order_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
