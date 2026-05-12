"""
Logger estruturado com rotação de arquivo.

Por que logger estruturado?
    print() funciona em desenvolvimento. Em produção, você precisa:
    - Saber QUANDO aconteceu (timestamp)
    - Saber ONDE aconteceu (módulo, linha)
    - Filtrar por nível (INFO vs ERROR vs DEBUG)
    - Arquivo rotativo que não enche o disco

Regra de ouro nos logs:
    Logue o EVENTO, nunca o DADO.
    ✅ "Usuário id=abc solicitou redefinição de senha"
    ❌ "Usuário email=fulano@email.com senha=abc123 fez login"
    
    Dado pessoal em log = violação LGPD e risco de segurança.

Por que RotatingFileHandler?
    Um arquivo de log sem rotação cresce para sempre.
    5MB por arquivo, 5 backups = máximo 25MB em disco.
"""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler


def get_logger(name: str, log_dir: str = "logs") -> logging.Logger:
    """
    Retorna um logger configurado com handlers de console e arquivo.

    Idempotente: chamadas múltiplas para o mesmo `name` retornam o mesmo logger
    sem duplicar handlers.

    Args:
        name:    Nome do logger — use __name__ no módulo.
                 Ex: get_logger(__name__)
        log_dir: Diretório onde os arquivos de log serão criados.

    Returns:
        Logger configurado e pronto para uso.

    Uso:
        from src.utils.logger import get_logger
        logger = get_logger(__name__)

        logger.info("order.created", extra={"order_id": order.public_id})
        logger.error("payment.failed", extra={"reason": result.error})
        logger.warning("rate_limit.exceeded", extra={"ip": request.remote_addr})
    """
    logger = logging.getLogger(name)

    # Evita adicionar handlers duplicados em reload ou múltiplas chamadas
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    # Console — INFO e acima em produção, DEBUG em dev
    console_level = logging.DEBUG if os.getenv("APP_ENV") == "development" else logging.INFO
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Arquivo com rotação — 5MB por arquivo, 5 backups
    try:
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f"{name.split('.')[-1]}.log")
        file_handler = RotatingFileHandler(
            filename=log_file,
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        logger.warning(f"File logging unavailable: {e}")

    return logger


# Logger raiz da aplicação
app_logger = get_logger("app")
