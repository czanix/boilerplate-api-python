"""Order entity — regras de negócio puras, zero dependência externa."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4


@dataclass
class OrderItem:
    product_id: str
    quantity: int
    unit_price: Decimal

    def __post_init__(self):
        if self.quantity <= 0:
            raise ValueError("Quantity must be positive")
        if self.unit_price < 0:
            raise ValueError("Price cannot be negative")


@dataclass
class Order:
    customer_id: str
    items: list[OrderItem]
    id: int | None = None
    public_id: str = field(default_factory=lambda: str(uuid4()))
    status: str = "pending"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    deleted_at: datetime | None = None

    def __post_init__(self):
        if not self.items:
            raise ValueError("Pedido deve ter pelo menos um item")

    @property
    def total(self) -> Decimal:
        return sum(i.quantity * i.unit_price for i in self.items)

    def cancel(self) -> None:
        if self.status == "delivered":
            raise ValueError("Cannot cancel delivered order")
        if self.status == "cancelled":
            raise ValueError("Already cancelled")
        self.status = "cancelled"
        self.updated_at = datetime.now(timezone.utc)
