"""
Prometheus metrics for monitoring.
Exposes HTTP endpoint at /metrics for Prometheus scraping.
"""

from __future__ import annotations

import logging
import time
from typing import Callable

from fastapi import Request
from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    Info,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

logger = logging.getLogger(__name__)

# ============================================================================
# Application Info
# ============================================================================
app_info = Info("radar_precios", "Radar de Precios - Price Comparison API")
app_info.info({
    "version": "0.2.0-fase-a",
    "description": "Comparador de precios de supermercados chilenos",
})


# ============================================================================
# Request Metrics
# ============================================================================
request_count = Counter(
    "radar_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

request_duration = Histogram(
    "radar_http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

request_size = Histogram(
    "radar_http_request_size_bytes",
    "HTTP request size",
    ["method", "endpoint"],
    buckets=[100, 500, 1000, 5000, 10000, 50000],
)

response_size = Histogram(
    "radar_http_response_size_bytes",
    "HTTP response size",
    ["method", "endpoint"],
    buckets=[100, 500, 1000, 5000, 10000, 50000, 100000],
)

active_requests = Gauge(
    "radar_http_active_requests",
    "Active HTTP requests",
    ["method", "endpoint"],
)


# ============================================================================
# Search Metrics
# ============================================================================
search_requests = Counter(
    "radar_search_requests_total",
    "Total search requests",
    ["store", "status"],
)

search_duration = Histogram(
    "radar_search_duration_seconds",
    "Search request latency",
    ["store"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0],
)

search_results_count = Histogram(
    "radar_search_results_count",
    "Number of search results",
    ["store"],
    buckets=[1, 5, 10, 20, 50, 100],
)

cache_hits = Counter(
    "radar_cache_hits_total",
    "Cache hits",
    ["type"],
)

cache_misses = Counter(
    "radar_cache_misses_total",
    "Cache misses",
    ["type"],
)


# ============================================================================
# Database Metrics
# ============================================================================
db_queries_total = Counter(
    "radar_db_queries_total",
    "Total database queries",
    ["operation", "table"],
)

db_query_duration = Histogram(
    "radar_db_query_duration_seconds",
    "Database query latency",
    ["operation", "table"],
    buckets=[0.001, 0.01, 0.05, 0.1, 0.5, 1.0],
)

db_connection_pool_size = Gauge(
    "radar_db_connection_pool_size",
    "Database connection pool size",
)

db_connection_pool_checked_out = Gauge(
    "radar_db_connection_pool_checked_out",
    "Checked out connections from pool",
)


# ============================================================================
# Redis Metrics
# ============================================================================
redis_commands_total = Counter(
    "radar_redis_commands_total",
    "Total Redis commands",
    ["command"],
)

redis_command_duration = Histogram(
    "radar_redis_command_duration_seconds",
    "Redis command latency",
    ["command"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1],
)

redis_connection_errors = Counter(
    "radar_redis_connection_errors_total",
    "Redis connection errors",
)


# ============================================================================
# Celery Metrics
# ============================================================================
celery_tasks_total = Counter(
    "radar_celery_tasks_total",
    "Total Celery tasks",
    ["task_name", "status"],
)

celery_task_duration = Histogram(
    "radar_celery_task_duration_seconds",
    "Celery task execution time",
    ["task_name"],
    buckets=[1, 5, 10, 30, 60, 300, 600],
)

celery_active_tasks = Gauge(
    "radar_celery_active_tasks",
    "Active Celery tasks",
    ["task_name"],
)

celery_worker_online = Gauge(
    "radar_celery_worker_online",
    "Number of online workers",
)

celery_queue_size = Gauge(
    "radar_celery_queue_size",
    "Celery queue size",
    ["queue"],
)


# ============================================================================
# Business Metrics
# ============================================================================
basket_count = Gauge(
    "radar_baskets_count",
    "Total baskets",
)

basket_items_count = Gauge(
    "radar_basket_items_count",
    "Total items in all baskets",
)

users_count = Gauge(
    "radar_users_count",
    "Total users",
)

products_count = Gauge(
    "radar_products_count",
    "Total products indexed",
    ["store"],
)

price_updates = Counter(
    "radar_price_updates_total",
    "Total price updates",
    ["store"],
)


# ============================================================================
# Error Metrics
# ============================================================================
exceptions_total = Counter(
    "radar_exceptions_total",
    "Total exceptions",
    ["exception_type"],
)

http_errors = Counter(
    "radar_http_errors_total",
    "HTTP errors",
    ["status_code"],
)

rate_limit_exceeded = Counter(
    "radar_rate_limit_exceeded_total",
    "Rate limit exceeded",
    ["endpoint"],
)


# ============================================================================
# System Metrics
# ============================================================================
app_version = Info(
    "radar_version",
    "Application version",
)

app_uptime = Gauge(
    "radar_uptime_seconds",
    "Application uptime",
)


# ============================================================================
# Middleware for request metrics
# ============================================================================
async def metrics_middleware(request: Request, call_next: Callable) -> any:
    """Middleware to collect request/response metrics."""
    
    method = request.method
    path = request.url.path
    endpoint = f"{method} {path}"
    
    # Start timing
    start_time = time.time()
    active_requests.labels(method=method, endpoint=endpoint).inc()
    
    try:
        # Get request size
        body = await request.body()
        request_size.labels(method=method, endpoint=endpoint).observe(len(body))
        
        # Call the actual endpoint
        response = await call_next(request)
        
        # Record metrics
        duration = time.time() - start_time
        request_duration.labels(method=method, endpoint=endpoint).observe(duration)
        request_count.labels(
            method=method,
            endpoint=endpoint,
            status_code=response.status_code,
        ).inc()
        
        # Get response size
        if "content-length" in response.headers:
            response_size.labels(method=method, endpoint=endpoint).observe(
                int(response.headers["content-length"])
            )
        
        # Record errors
        if response.status_code >= 400:
            http_errors.labels(status_code=response.status_code).inc()
        
        return response
    
    except Exception as e:
        exceptions_total.labels(exception_type=type(e).__name__).inc()
        raise
    
    finally:
        active_requests.labels(method=method, endpoint=endpoint).dec()


def get_metrics_response():
    """Get Prometheus metrics in text format."""
    return generate_latest(), CONTENT_TYPE_LATEST


# ============================================================================
# Helper functions for recording metrics
# ============================================================================
def record_search_request(store: str, success: bool):
    """Record a search request."""
    status = "success" if success else "error"
    search_requests.labels(store=store, status=status).inc()


def record_search_duration(store: str, duration: float):
    """Record search duration."""
    search_duration.labels(store=store).observe(duration)


def record_db_query(operation: str, table: str, duration: float):
    """Record a database query."""
    db_queries_total.labels(operation=operation, table=table).inc()
    db_query_duration.labels(operation=operation, table=table).observe(duration)


def record_redis_command(command: str, duration: float, success: bool = True):
    """Record a Redis command."""
    redis_commands_total.labels(command=command).inc()
    redis_command_duration.labels(command=command).observe(duration)
    
    if not success:
        redis_connection_errors.inc()


def record_celery_task(task_name: str, duration: float, status: str):
    """Record a Celery task execution."""
    celery_tasks_total.labels(task_name=task_name, status=status).inc()
    celery_task_duration.labels(task_name=task_name).observe(duration)
