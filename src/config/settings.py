"""
Settings — configuração validada via Pydantic.

Por que Pydantic para settings?
    Variável de ambiente faltando → erro claro na startup.
    Tipo errado (porta como texto) → erro claro na startup.
    
    Sem isso: a aplicação sobe, funciona "mais ou menos",
    e o erro aparece em produção no pior momento.

Regra: a aplicação NUNCA deve subir com configuração inválida.
    Falhar rápido na inicialização é infinitamente melhor
    que falhar silenciosamente 30 minutos depois de produção no ar.

Hierarquia de configuração:
    1. Variáveis de ambiente (produção)
    2. Arquivo .env (desenvolvimento local)
    3. Valores default (quando seguro ter um)
"""

from __future__ import annotations

import os
from functools import lru_cache

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configurações da aplicação validadas na startup.

    Qualquer campo sem default que não estiver no ambiente
    levanta ValidationError antes da aplicação subir.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # ignora variáveis extras no .env
    )

    # Aplicação
    app_name: str = "czanix-api"
    app_version: str = "0.1.0"
    app_env: str = "development"  # development | staging | production
    debug: bool = False

    # Servidor
    host: str = "0.0.0.0"
    port: int = 8000

    # Banco de dados PostgreSQL
    database_url: str  # obrigatório — sem default
    db_pool_min: int = 2
    db_pool_max: int = 10

    # Redis (opcional)
    redis_url: str | None = None

    # Segurança
    secret_key: str  # obrigatório — sem default
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60  # 1 hora — padrão seguro

    @field_validator("app_env")
    @classmethod
    def validate_env(cls, v: str) -> str:
        allowed = {"development", "staging", "production"}
        if v not in allowed:
            raise ValueError(f"APP_ENV deve ser um de: {allowed}")
        return v

    @field_validator("port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        if not (1024 <= v <= 65535):
            raise ValueError("PORT deve estar entre 1024 e 65535")
        return v

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        """Em produção, configurações inseguras devem falhar."""
        if self.app_env == "production":
            if self.debug:
                raise ValueError("DEBUG não pode ser True em produção")
            if len(self.secret_key) < 32:
                raise ValueError("SECRET_KEY deve ter pelo menos 32 caracteres em produção")
        return self

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Retorna as settings como singleton.

    lru_cache garante que a validação roda apenas uma vez.
    Em testes, use: get_settings.cache_clear() para resetar.
    """
    return Settings()


# Singleton exportado
settings = get_settings()
