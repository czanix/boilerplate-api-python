"""Order controller — FastAPI router fino."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])


class CreateOrderRequest(BaseModel):
    customer_id: str
    items: list[dict]


@router.post("/", status_code=201)
async def create_order(request: CreateOrderRequest):
    """Create a new order — injete use case via DI."""
    # DI será configurado no main.py
    return {"message": "Configure dependency injection in main.py"}
