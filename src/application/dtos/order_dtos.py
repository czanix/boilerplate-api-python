from dataclasses import dataclass
from ...domain.entities.order import Order


@dataclass
class ItemInput:
    product_id: str
    quantity: int
    unit_price: float


@dataclass
class CreateOrderInput:
    customer_id: str
    items: list[ItemInput]


@dataclass
class OrderOutput:
    public_id: str
    customer_id: str
    status: str
    total: float
    created_at: str

    @staticmethod
    def from_entity(order: Order) -> "OrderOutput":
        return OrderOutput(
            public_id=order.public_id,
            customer_id=order.customer_id,
            status=order.status,
            total=float(order.total),
            created_at=order.created_at.isoformat(),
        )
