"""Testes do domínio — zero dependência externa."""
import pytest
from decimal import Decimal
from src.domain.entities.order import Order, OrderItem


class TestOrder:
    def test_create_order_with_items(self):
        items = [OrderItem(product_id="prod-1", quantity=2, unit_price=Decimal("29.90"))]
        order = Order(customer_id="customer-123", items=items)

        assert order.customer_id == "customer-123"
        assert order.status == "pending"
        assert order.total == Decimal("59.80")

    def test_empty_items_raises_error(self):
        with pytest.raises(ValueError, match="pelo menos um item"):
            Order(customer_id="customer-123", items=[])

    def test_cancel_order(self):
        items = [OrderItem(product_id="prod-1", quantity=1, unit_price=Decimal("10"))]
        order = Order(customer_id="customer-123", items=items)
        order.cancel()
        assert order.status == "cancelled"

    def test_cancel_delivered_raises_error(self):
        items = [OrderItem(product_id="prod-1", quantity=1, unit_price=Decimal("10"))]
        order = Order(customer_id="customer-123", items=items, status="delivered")
        with pytest.raises(ValueError, match="Cannot cancel"):
            order.cancel()

    def test_negative_quantity_raises_error(self):
        with pytest.raises(ValueError, match="positive"):
            OrderItem(product_id="prod-1", quantity=-1, unit_price=Decimal("10"))
