"""Create Order use case — orquestra domínio + infra."""
from decimal import Decimal
from ..dtos.order_dtos import CreateOrderInput, OrderOutput
from ...domain.result import Result, ok, fail
from ...domain.entities.order import Order, OrderItem
from ...domain.repositories.order_repository import OrderRepository


class CreateOrderUseCase:
    def __init__(self, repository: OrderRepository):
        self._repository = repository

    async def execute(self, input_data: CreateOrderInput) -> Result:
        if not input_data.items:
            return fail("Pedido deve ter pelo menos um item")

        if not input_data.customer_id:
            return fail("Cliente obrigatório")

        items = [
            OrderItem(
                product_id=i.product_id,
                quantity=i.quantity,
                unit_price=Decimal(str(i.unit_price)),
            )
            for i in input_data.items
        ]

        order = Order(customer_id=input_data.customer_id, items=items)
        await self._repository.save(order)

        return ok(OrderOutput.from_entity(order))
