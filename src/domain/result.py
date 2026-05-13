"""
Result Pattern — sem exceção para fluxo de negócio.

Exceção é para o inesperado (banco caiu, memória cheia).
"Email já cadastrado" NÃO é exceção — é fluxo de negócio.
"""
from dataclasses import dataclass
from typing import TypeVar, Generic

T = TypeVar("T")


@dataclass(frozen=True)
class Ok(Generic[T]):
    value: T
    ok: bool = True


@dataclass(frozen=True)
class Fail:
    error: str
    ok: bool = False


Result = Ok[T] | Fail


def ok(value: T) -> Ok[T]:
    return Ok(value=value)


def fail(error: str) -> Fail:
    return Fail(error=error)
