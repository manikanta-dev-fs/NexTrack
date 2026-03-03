"""
Performance Enhancements - Logging and Monitoring

Structured logging, performance monitoring, metrics collection, and error tracking.
"""

import logging
import json
import time
import uuid
from datetime import datetime
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# Configure structured JSON logging
class JSONFormatter(logging.Formatter):
    """Format logs as JSON for better parsing."""
    
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        if hasattr(record, 'extra'):
            log_data.update(record.extra)
        
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


# Setup logger
logger = logging.getLogger("nextrack")
logger.setLevel(logging.INFO)

# Console handler with JSON formatting
console_handler = logging.StreamHandler()
console_handler.setFormatter(JSONFormatter())
logger.addHandler(console_handler)

# File handler
file_handler = logging.FileHandler("logs/nextrack.log")
file_handler.setFormatter(JSONFormatter())
logger.addHandler(file_handler)


class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """
    Middleware to monitor API performance.
    
    Logs:
    - Request/response times
    - Status codes
    - Slow queries (>1s)
    - Request IDs for tracing
    
    Wires into MetricsCollector for aggregate stats.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        request_id = str(uuid.uuid4())
        
        # Log incoming request
        logger.info(
            "Incoming request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "client": request.client.host if request.client else None
            }
        )
        
        # Process request
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            
            # Record metrics
            metrics.record_request(request.url.path, process_time, response.status_code)
            
            # Log response
            log_level = logging.INFO if response.status_code < 400 else logging.WARNING
            logger.log(
                log_level,
                "Request completed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "process_time": f"{process_time:.3f}s"
                }
            )
            
            # Warn on slow requests
            if process_time > 1.0:
                logger.warning(
                    "Slow request detected",
                    extra={
                        "request_id": request_id,
                        "method": request.method,
                        "path": request.url.path,
                        "process_time": f"{process_time:.3f}s"
                    }
                )
            
            # Add tracing headers
            response.headers["X-Process-Time"] = f"{process_time:.3f}"
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            metrics.record_request(request.url.path, process_time, 500)
            logger.error(
                "Request failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "error": str(e),
                    "process_time": f"{process_time:.3f}s"
                },
                exc_info=True
            )
            raise


class ErrorTrackingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for error tracking and reporting.
    
    Captures and logs all exceptions with context.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        except Exception as e:
            # Log error with full context
            logger.error(
                "Unhandled exception",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "query_params": dict(request.query_params),
                    "client": request.client.host if request.client else None,
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                },
                exc_info=True
            )
            
            # Re-raise to let FastAPI handle it
            raise


# Metrics collection (simple in-memory for now)
class MetricsCollector:
    """Simple metrics collector for monitoring."""
    
    def __init__(self):
        self.request_count = 0
        self.error_count = 0
        self.total_response_time = 0.0
        self.endpoint_metrics = {}
    
    def record_request(self, endpoint: str, response_time: float, status_code: int):
        """Record request metrics."""
        self.request_count += 1
        self.total_response_time += response_time
        
        if status_code >= 400:
            self.error_count += 1
        
        if endpoint not in self.endpoint_metrics:
            self.endpoint_metrics[endpoint] = {
                "count": 0,
                "total_time": 0.0,
                "errors": 0
            }
        
        self.endpoint_metrics[endpoint]["count"] += 1
        self.endpoint_metrics[endpoint]["total_time"] += response_time
        
        if status_code >= 400:
            self.endpoint_metrics[endpoint]["errors"] += 1
    
    def get_metrics(self):
        """Get current metrics."""
        avg_response_time = (
            self.total_response_time / self.request_count
            if self.request_count > 0
            else 0
        )
        
        return {
            "total_requests": self.request_count,
            "total_errors": self.error_count,
            "error_rate": round(
                self.error_count / self.request_count if self.request_count > 0 else 0, 4
            ),
            "avg_response_time": f"{avg_response_time:.3f}s",
            "endpoints": self.endpoint_metrics
        }


# Global metrics collector
metrics = MetricsCollector()
