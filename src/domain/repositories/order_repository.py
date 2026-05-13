"""Repository interface — contrato que o domínio define."""
from abc import ABC, abstractmethod
from ..entities.order import Order


class OrderRepository(ABC):
    @abstractmethod
    async def save(self, order: Order) -> None: ...

    @abstractmethod
    async def find_by_public_id(self, public_id: str) -> Order | None: ...

    @abstractmethod
    async def update(self, order: Order) -> None: ...

    @abstractmethod
    async def soft_delete(self, public_id: str) -> None: ...
