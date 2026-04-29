"""
Manejo centralizado de errores para Radar de Precios.
Proporciona respuestas consistentes y logging estructurado.
"""
import logging
import traceback
from typing import Union

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from backend.search_service import SearchServiceError
from backend.scraper import ScraperError, NoResultsError


logger = logging.getLogger(__name__)


class APIError(Exception):
    """Clase base para errores de API."""
    
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = "INTERNAL_ERROR",
        details: dict | None = None
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}


class NotFoundError(APIError):
    """Recurso no encontrado."""
    
    def __init__(self, resource: str, resource_id: str):
        super().__init__(
            message=f"{resource} no encontrado: {resource_id}",
            status_code=404,
            error_code="NOT_FOUND",
            details={"resource": resource, "id": resource_id}
        )


class ValidationAPIError(APIError):
    """Error de validación de entrada."""
    
    def __init__(self, message: str, details: dict | None = None):
        super().__init__(
            message=message,
            status_code=422,
            error_code="VALIDATION_ERROR",
            details=details
        )


class AuthenticationError(APIError):
    """Error de autenticación."""
    
    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            message=message,
            status_code=401,
            error_code="AUTHENTICATION_ERROR"
        )


class AuthorizationError(APIError):
    """Error de autorización."""
    
    def __init__(self, message: str = "Not authorized"):
        super().__init__(
            message=message,
            status_code=403,
            error_code="AUTHORIZATION_ERROR"
        )


class ExternalServiceError(APIError):
    """Error de servicio externo (scraper, etc)."""
    
    def __init__(self, service: str, message: str):
        super().__init__(
            message=f"Error en {service}: {message}",
            status_code=502,
            error_code="EXTERNAL_SERVICE_ERROR",
            details={"service": service}
        )


def _format_validation_error(error: ValidationError) -> list[dict]:
    """Formatear errores de Pydantic para respuesta JSON."""
    errors = []
    for e in error.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in e["loc"]),
            "message": e["msg"],
            "type": e["type"],
        })
    return errors


async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """Manejador para errores personalizados de API."""
    logger.warning(
        f"API Error: {exc.error_code} - {exc.message}",
        extra={
            "error_code": exc.error_code,
            "path": str(request.url.path),
            "method": request.method,
            "details": exc.details,
        }
    )
    
    content = {
        "error": exc.error_code,
        "message": exc.message,
    }
    if exc.details:
        content["details"] = exc.details
    
    return JSONResponse(
        status_code=exc.status_code,
        content=content
    )


async def validation_error_handler(
    request: Request, 
    exc: Union[RequestValidationError, ValidationError]
) -> JSONResponse:
    """Manejador para errores de validación de FastAPI/Pydantic."""
    logger.warning(
        f"Validation Error: {exc.errors()}",
        extra={
            "path": str(request.url.path),
            "method": request.method,
        }
    )
    
    if isinstance(exc, RequestValidationError):
        errors = [{"field": ".".join(str(l) for l in e["loc"]), "message": e["msg"]} for e in exc.errors()]
    else:
        errors = _format_validation_error(exc)
    
    return JSONResponse(
        status_code=422,
        content={
            "error": "VALIDATION_ERROR",
            "message": "Error de validación",
            "details": {"fields": errors}
        }
    )


async def search_service_error_handler(
    request: Request, 
    exc: SearchServiceError
) -> JSONResponse:
    """Manejador para errores del servicio de búsqueda."""
    logger.error(
        f"Search Service Error: {exc.message}",
        extra={
            "status_code": exc.status_code,
            "path": str(request.url.path),
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "SEARCH_ERROR",
            "message": exc.message,
        }
    )


async def scraper_error_handler(request: Request, exc: ScraperError) -> JSONResponse:
    """Manejador para errores del scraper."""
    logger.error(
        f"Scraper Error: {str(exc)}",
        extra={"path": str(request.url.path)}
    )
    
    return JSONResponse(
        status_code=502,
        content={
            "error": "SCRAPER_ERROR",
            "message": "Error al obtener datos del supermercado",
        }
    )


async def no_results_error_handler(request: Request, exc: NoResultsError) -> JSONResponse:
    """Manejador para cuando no hay resultados."""
    logger.info(
        f"No Results: {exc.query}",
        extra={"suggestions": exc.suggestions}
    )
    
    content = {
        "error": "NO_RESULTS",
        "message": exc.message or f"No se encontraron productos para '{exc.query}'",
    }
    if exc.suggestions:
        content["suggestions"] = exc.suggestions
    
    return JSONResponse(status_code=404, content=content)


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Manejador genérico para excepciones no controladas."""
    logger.error(
        f"Unhandled Exception: {type(exc).__name__}: {str(exc)}\n{traceback.format_exc()}",
        extra={
            "path": str(request.url.path),
            "method": request.method,
            "exception_type": type(exc).__name__,
        }
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_ERROR",
            "message": "Error interno del servidor",
        }
    )


def register_exception_handlers(app: FastAPI):
    """Registrar todos los manejadores de excepciones."""
    app.add_exception_handler(APIError, api_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(ValidationError, validation_error_handler)
    app.add_exception_handler(SearchServiceError, search_service_error_handler)
    app.add_exception_handler(ScraperError, scraper_error_handler)
    app.add_exception_handler(NoResultsError, no_results_error_handler)
    app.add_exception_handler(Exception, generic_exception_handler)