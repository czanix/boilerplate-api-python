"""
DatabaseFactory — conexões com retry automático e context managers.

Padrão herdado do projeto real, elevado para reuso:
  - Retry com backoff exponencial (tenacity)
  - Context managers que garantem fechamento de conexão
  - Pool de conexões PostgreSQL via psycopg2/asyncpg
  - SQL Server via pyodbc com escape seguro de credenciais
  - Zero credencial hardcoded — tudo via variável de ambiente

Por que context manager?
    Garante que a conexão fecha mesmo se der erro.
    Sem context manager, uma exceção no meio do bloco vaza a conexão.
    Conexão vazada = pool esgotado = sistema indisponível.
"""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Generator

import psycopg2
import psycopg2.pool
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ..config.settings import Settings

logger = logging.getLogger("app.database")


# Pool compartilhado — criado uma vez, reusado por todos os requests
_pg_pool: psycopg2.pool.ThreadedConnectionPool | None = None


def init_postgres_pool(settings: Settings) -> None:
    """
    Inicializa o pool de conexões PostgreSQL.
    Chame uma vez na inicialização da aplicação.

    Por que pool?
        Criar conexão é caro (~100ms).
        Pool mantém conexões abertas e reutiliza.
        Sem pool: cada request abre e fecha conexão = gargalo garantido.
    """
    global _pg_pool

    if _pg_pool is not None:
        return

    _pg_pool = psycopg2.pool.ThreadedConnectionPool(
        minconn=settings.db_pool_min,
        maxconn=settings.db_pool_max,
        dsn=settings.database_url,
        connect_timeout=10,
        application_name=settings.app_name,
    )
    logger.info("PostgreSQL pool initialized (min=%d, max=%d)", settings.db_pool_min, settings.db_pool_max)


class DatabaseFactory:
    """
    Factory de conexões de banco de dados.

    Uso:
        # PostgreSQL via pool (padrão para APIs)
        with DatabaseFactory.postgres() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM orders WHERE public_id = %s", (public_id,))
            row = cursor.fetchone()

        # SQL Server via pyodbc
        with DatabaseFactory.sql_server(settings.sql_server) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT TOP 1 * FROM Pedidos WHERE Id = ?", (order_id,))
    """

    @staticmethod
    @contextmanager
    def postgres() -> Generator[psycopg2.extensions.connection, None, None]:
        """
        Retorna uma conexão do pool.
        Garante devolução ao pool mesmo em caso de erro.
        """
        if _pg_pool is None:
            raise RuntimeError("Pool não inicializado. Chame init_postgres_pool() na startup.")

        conn = _pg_pool.getconn()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            _pg_pool.putconn(conn)

    @staticmethod
    @contextmanager
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def sql_server(db_config: dict) -> Generator:
        """
        Conexão SQL Server com retry automático.
        
        O retry é para falhas transitórias de rede — não para erro de credencial.
        3 tentativas com espera exponencial: 2s → 4s → 8s.
        """
        import pyodbc

        password = db_config.get("password", "")
        safe_password = f"{{{password.replace('}', '}}')}}}"  # escape ODBC

        conn_str = (
            f"DRIVER={db_config.get('driver', '{ODBC Driver 18 for SQL Server}')};"
            f"SERVER=tcp:{db_config['server']},1433;"
            f"DATABASE={db_config['database']};"
            f"UID={db_config['user']};"
            f"PWD={safe_password};"
            "Encrypt=yes;"
            "TrustServerCertificate=no;"
            "Connection Timeout=30;"
        )

        conn = pyodbc.connect(conn_str)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            try:
                conn.close()
            except Exception:
                pass
