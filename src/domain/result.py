"""
Result Pattern para Python.

O conceito: uma função retorna SEMPRE sucesso ou falha de forma explícita.
Sem lançar exceção para fluxo de negócio — exceção é para o inesperado.

Por que isso importa?
    "Email já cadastrado" não é exceção. É regra de negócio.
    "Banco de dados caiu" é exceção.

Usar exceção para controle de fluxo:
    - Esconde erros no callstack
    - Força o chamador a saber qual exceção capturar
    - Não aparece no tipo de retorno da função

Result<T> resolve isso: o chamador é obrigado a lidar com ambos os casos.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import TypeVar, Generic, Optional, Callable, Any

T = TypeVar('T')
E = TypeVar('E', bound=str)


@dataclass(frozen=True)
class Ok(Generic[T]):
    """Representa sucesso com um valor."""
    value: T
    ok: bool = True

    def unwrap(self) -> T:
        return self.value

    def unwrap_or(self, default: T) -> T:
        return self.value

    def map(self, fn: Callable[[T], Any]) -> 'Ok':
        return Ok(fn(self.value))


@dataclass(frozen=True)
class Err(Generic[E]):
    """Representa falha com um código de erro."""
    error: E
    ok: bool = False

    def unwrap(self) -> None:
        raise ValueError(f"Called unwrap() on Err: {self.error}")

    def unwrap_or(self, default: Any) -> Any:
        return default

    def map(self, fn: Callable) -> 'Err':
        return self  # Err propaga sem transformar


# O tipo Result — ou Ok[T] ou Err[E]
Result = Ok[T] | Err[str]


# --- Helpers ---

def ok(value: T) -> Ok[T]:
    """Cria um resultado de sucesso."""
    return Ok(value)


def err(error: str) -> Err[str]:
    """Cria um resultado de falha."""
    return Err(error)


# --- Exemplo de uso ---
#
# def criar_usuario(email: str, senha: str) -> Result[Usuario]:
#     if usuario_existe(email):
#         return err("EMAIL_JA_CADASTRADO")       # Fluxo de negócio — não é exceção
#
#     usuario = Usuario(email=email, senha=hash(senha))
#     salvar(usuario)
#     return ok(usuario)                           # Sucesso
#
# # O chamador é forçado a verificar ambos os casos
# resultado = criar_usuario(email, senha)
#
# if not resultado.ok:
#     return {"erro": resultado.error}, 422        # Erro de negócio
#
# return {"id": resultado.value.public_id}, 201   # Sucesso
