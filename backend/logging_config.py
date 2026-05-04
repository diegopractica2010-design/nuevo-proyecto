"""
Logging estructurado para Radar de Precios.
Configura logging JSON con correlation IDs.
"""
import logging
import sys
import json
import uuid
from datetime import UTC, datetime
from contextvars import ContextVar

from fastapi import Request

# ContextVar para correlation ID
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


def get_correlation_id() -> str:
    """Obtener correlation ID actual o generar uno nuevo."""
    cid = correlation_id_var.get()
    if not cid:
        cid = str(uuid.uuid4())[:8]
        correlation_id_var.set(cid)
    return cid


class JSONFormatter(logging.Formatter):
    """Formateador de logs en formato JSON."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": get_correlation_id(),
        }
        
        # Agregar información extra
        if hasattr(record, "extra"):
            for key, value in record.extra.items():
                if key not in ["msg", "args", "exc_info", "exc_text", "stack_info"]:
                    log_data[key] = value
        
        # Agregar información de excepción
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Agregar información de request si está disponible
        if hasattr(record, "request"):
            request = record.request
            log_data["request"] = {
                "method": request.method,
                "path": str(request.url.path),
                "client": request.client.host if request.client else None,
            }
        
        return json.dumps(log_data)


def setup_logging(level: str = "INFO", json_format: bool = False):
    """Configurar logging de la aplicación."""
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    handler = logging.StreamHandler(sys.stdout)
    
    if json_format:
        handler.setFormatter(JSONFormatter())
    else:
        # Formato legible para desarrollo
        handler.setFormatter(logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        ))
    
    # Configurar root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    
    # Reducir ruido de libraries
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    
    return root_logger


def log_request(request: Request) -> dict:
    """Crear contexto de logging para un request."""
    return {
        "request": {
            "method": request.method,
            "path": str(request.url.path),
            "query_params": dict(request.query_params),
            "client": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
        },
        "correlation_id": get_correlation_id(),
    }


class LogContext:
    """Contexto temporal para logging."""
    
    def __init__(self, **kwargs):
        self.extra = kwargs
        self._old_factory = None
    
    def __enter__(self):
        self._old_factory = logging.getLogRecordFactory()
        
        def record_factory(*args, **factory_kwargs):
            record = self._old_factory(*args, **factory_kwargs)
            for key, value in self.extra.items():
                setattr(record, key, value)
            return record
        
        logging.setLogRecordFactory(record_factory)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        logging.setLogRecordFactory(self._old_factory)
