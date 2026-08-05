from fastapi import FastAPI, HTTPException
from uuid import UUID, uuid4
from pydantic import BaseModel
from decimal import Decimal
from typing import List

from application.commands.create_order import CreateOrderCommand, CreateOrderHandler
from infrastructure.repositories.in_memory_order_repository import InMemoryOrderRepository

app = FastAPI(title="Qore API")

# Dependencias
repo = InMemoryOrderRepository()
handler = CreateOrderHandler(repo)

class OrderItemDTO(BaseModel):
    product_id: UUID
    qty: int
    price: float

class CreateOrderRequest(BaseModel):
    customer_id: UUID
    items: List[OrderItemDTO]
    notes: str = None

@app.post("/orders")
def create_order(req: CreateOrderRequest):
    cmd = CreateOrderCommand(
        customer_id=req.customer_id,
        items=[{"product_id": i.product_id, "qty": i.qty, "price": i.price} for i in req.items],
        notes=req.notes
    )
    order = handler.handle(cmd)
    return {"order_id": str(order.id), "total": str(order.total.amount), "state": order.state.value}

@app.get("/health")
def health():
    return {"status": "ok"}
