"""Middleware implementations (Fase A)."""

from __future__ import annotations

import logging
import time
import uuid
from typing import Callable

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from backend.rate_limiter import get_rate_limiter

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Real rate limiting middleware using Redis (FASE A).
    
    Limits requests per IP using sliding window algorithm.
    Configuration: RATE_LIMIT_REQUESTS_PER_MINUTE via environment or config.
    
    Graceful degradation: If Redis unavailable, allows all requests.
    """
    
    # Endpoints excluded from rate limiting
    EXCLUDED_PATHS = {
        "/health",
        "/",
        "/docs",
        "/openapi.json",
        "/redoc",
    }
    
    def __init__(self, app: FastAPI):
        super().__init__(app)
        self.rate_limiter = get_rate_limiter()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request through rate limiter."""
        
        # Skip rate limiting for certain paths
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)
        
        # Check rate limit
        is_limited, metadata = self.rate_limiter.is_rate_limited(request)
        
        if is_limited:
            logger.warning(
                f"Rate limit exceeded: IP={metadata.get('ip')}, "
                f"Window={metadata.get('window')}s, "
                f"RetryAfter={metadata.get('retry_after')}s"
            )
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests. Please try again later.",
                    "retry_after": metadata.get("retry_after", 60),
                },
                headers={
                    "Retry-After": str(metadata.get("retry_after", 60)),
                    "X-RateLimit-Limit": str(metadata.get("limit")),
                    "X-RateLimit-Window": str(metadata.get("window")),
                },
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers to response
        if metadata.get("allowed"):
            response.headers["X-RateLimit-Limit"] = str(metadata.get("limit", 10))
            response.headers["X-RateLimit-Remaining"] = str(metadata.get("remaining", 0))
        
        return response


class RequestIdMiddleware(BaseHTTPMiddleware):
    """
    Add request ID to all requests for tracing.
    
    Allows correlation of logs, traces, and errors.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add request ID to request context."""
        
        # Try to get existing request ID from headers
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())
        
        # Store in request state for later access
        request.state.request_id = request_id
        
        # Process request
        response = await call_next(request)
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Log all HTTP requests and responses.
    
    Useful for debugging and monitoring.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log request and response."""
        
        request_id = getattr(request.state, "request_id", "unknown")
        method = request.method
        path = request.url.path
        
        # Skip logging for health checks
        if path == "/health" or path == "/":
            return await call_next(request)
        
        start_time = time.time()
        
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            
            status_code = response.status_code
            log_level = logging.INFO if status_code < 400 else logging.WARNING if status_code < 500 else logging.ERROR
            
            logger.log(
                log_level,
                f"[{request_id}] {method} {path} - {status_code} - {duration:.3f}s"
            )
            
            return response
        
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"[{request_id}] {method} {path} - ERROR - {duration:.3f}s - {str(e)}",
                exc_info=True
            )
            raise
        
        # Agregar headers de rate limiting
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(limit - recent_count - 1)
        
        return response