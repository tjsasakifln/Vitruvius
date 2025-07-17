# Production use requires a separate commercial license from the Licensor.
# For commercial licenses, please contact Tiago Sasaki at tiago@confenge.com.br.

from typing import Optional, Dict, Any
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
import logging
import traceback
import uuid
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorCode(Enum):
    """Standardized error codes"""
    
    # Authentication & Authorization
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    ACCESS_DENIED = "ACCESS_DENIED"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"
    
    # Validation
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_INPUT = "INVALID_INPUT"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    
    # Resource Management
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    RESOURCE_ALREADY_EXISTS = "RESOURCE_ALREADY_EXISTS"
    RESOURCE_CONFLICT = "RESOURCE_CONFLICT"
    
    # File Operations
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    INVALID_FILE_TYPE = "INVALID_FILE_TYPE"
    UPLOAD_FAILED = "UPLOAD_FAILED"
    
    # Processing
    PROCESSING_ERROR = "PROCESSING_ERROR"
    PROCESSING_TIMEOUT = "PROCESSING_TIMEOUT"
    PROCESSING_FAILED = "PROCESSING_FAILED"
    
    # Database
    DATABASE_ERROR = "DATABASE_ERROR"
    DATABASE_CONNECTION_ERROR = "DATABASE_CONNECTION_ERROR"
    
    # External Services
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    EXTERNAL_SERVICE_UNAVAILABLE = "EXTERNAL_SERVICE_UNAVAILABLE"
    
    # Rate Limiting
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    
    # System
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"


class VitruviusException(Exception):
    """Base exception class for Vitruvius application"""
    
    def __init__(self, 
                 error_code: ErrorCode,
                 message: str,
                 details: Optional[Dict[str, Any]] = None,
                 http_status: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
                 user_message: Optional[str] = None):
        self.error_code = error_code
        self.message = message
        self.details = details or {}
        self.http_status = http_status
        self.user_message = user_message or self._get_user_friendly_message()
        self.error_id = str(uuid.uuid4())
        self.timestamp = datetime.utcnow()
        
        super().__init__(self.message)
    
    def _get_user_friendly_message(self) -> str:
        """Get user-friendly error message"""
        user_messages = {
            ErrorCode.INVALID_CREDENTIALS: "Invalid email or password",
            ErrorCode.ACCESS_DENIED: "Access denied",
            ErrorCode.TOKEN_EXPIRED: "Your session has expired. Please login again",
            ErrorCode.INSUFFICIENT_PERMISSIONS: "You don't have permission to perform this action",
            ErrorCode.VALIDATION_ERROR: "Please check your input and try again",
            ErrorCode.INVALID_INPUT: "The provided input is invalid",
            ErrorCode.MISSING_REQUIRED_FIELD: "Required information is missing",
            ErrorCode.RESOURCE_NOT_FOUND: "The requested resource was not found",
            ErrorCode.RESOURCE_ALREADY_EXISTS: "This resource already exists",
            ErrorCode.RESOURCE_CONFLICT: "There was a conflict with the requested operation",
            ErrorCode.FILE_NOT_FOUND: "File not found",
            ErrorCode.FILE_TOO_LARGE: "File is too large",
            ErrorCode.INVALID_FILE_TYPE: "Invalid file type",
            ErrorCode.UPLOAD_FAILED: "File upload failed",
            ErrorCode.PROCESSING_ERROR: "There was an error processing your request",
            ErrorCode.PROCESSING_TIMEOUT: "Request processing timed out",
            ErrorCode.PROCESSING_FAILED: "Processing failed",
            ErrorCode.DATABASE_ERROR: "A database error occurred",
            ErrorCode.DATABASE_CONNECTION_ERROR: "Database connection failed",
            ErrorCode.EXTERNAL_SERVICE_ERROR: "External service error",
            ErrorCode.EXTERNAL_SERVICE_UNAVAILABLE: "External service is unavailable",
            ErrorCode.RATE_LIMIT_EXCEEDED: "Too many requests. Please try again later",
            ErrorCode.INTERNAL_ERROR: "An internal error occurred",
            ErrorCode.SERVICE_UNAVAILABLE: "Service is temporarily unavailable"
        }
        
        return user_messages.get(self.error_code, "An unexpected error occurred")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for JSON response"""
        return {
            "error_code": self.error_code.value,
            "message": self.user_message,
            "error_id": self.error_id,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details if self.details else None
        }


class AuthenticationError(VitruviusException):
    """Authentication related errors"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code=ErrorCode.INVALID_CREDENTIALS,
            message=message,
            details=details,
            http_status=status.HTTP_401_UNAUTHORIZED
        )


class AuthorizationError(VitruviusException):
    """Authorization related errors"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code=ErrorCode.ACCESS_DENIED,
            message=message,
            details=details,
            http_status=status.HTTP_403_FORBIDDEN
        )


class ValidationError(VitruviusException):
    """Validation related errors"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code=ErrorCode.VALIDATION_ERROR,
            message=message,
            details=details,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class ResourceNotFoundError(VitruviusException):
    """Resource not found errors"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code=ErrorCode.RESOURCE_NOT_FOUND,
            message=message,
            details=details,
            http_status=status.HTTP_404_NOT_FOUND
        )


class ResourceConflictError(VitruviusException):
    """Resource conflict errors"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code=ErrorCode.RESOURCE_CONFLICT,
            message=message,
            details=details,
            http_status=status.HTTP_409_CONFLICT
        )


class FileError(VitruviusException):
    """File related errors"""
    
    def __init__(self, error_code: ErrorCode, message: str, details: Optional[Dict[str, Any]] = None):
        http_status = status.HTTP_400_BAD_REQUEST
        if error_code == ErrorCode.FILE_TOO_LARGE:
            http_status = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
        
        super().__init__(
            error_code=error_code,
            message=message,
            details=details,
            http_status=http_status
        )


class ProcessingError(VitruviusException):
    """Processing related errors"""
    
    def __init__(self, error_code: ErrorCode, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code=error_code,
            message=message,
            details=details,
            http_status=status.HTTP_422_UNPROCESSABLE_ENTITY
        )


class DatabaseError(VitruviusException):
    """Database related errors"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code=ErrorCode.DATABASE_ERROR,
            message=message,
            details=details,
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class ExternalServiceError(VitruviusException):
    """External service related errors"""
    
    def __init__(self, error_code: ErrorCode, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code=error_code,
            message=message,
            details=details,
            http_status=status.HTTP_502_BAD_GATEWAY
        )


class RateLimitError(VitruviusException):
    """Rate limiting errors"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
            message=message,
            details=details,
            http_status=status.HTTP_429_TOO_MANY_REQUESTS
        )


def create_error_handler():
    """Create standardized error handler for FastAPI"""
    
    async def vitruvius_exception_handler(request: Request, exc: VitruviusException) -> JSONResponse:
        """Handle VitruviusException"""
        
        # Log the error with full details
        logger.error(
            f"VitruviusException: {exc.error_code.value} - {exc.message}",
            extra={
                "error_id": exc.error_id,
                "error_code": exc.error_code.value,
                "http_status": exc.http_status,
                "details": exc.details,
                "path": request.url.path,
                "method": request.method,
                "user_agent": request.headers.get("User-Agent"),
                "client_ip": request.client.host
            }
        )
        
        return JSONResponse(
            status_code=exc.http_status,
            content=exc.to_dict()
        )
    
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        """Handle FastAPI HTTPException"""
        
        # Convert HTTPException to VitruviusException
        error_code = ErrorCode.INTERNAL_ERROR
        if exc.status_code == 401:
            error_code = ErrorCode.INVALID_CREDENTIALS
        elif exc.status_code == 403:
            error_code = ErrorCode.ACCESS_DENIED
        elif exc.status_code == 404:
            error_code = ErrorCode.RESOURCE_NOT_FOUND
        elif exc.status_code == 409:
            error_code = ErrorCode.RESOURCE_CONFLICT
        elif exc.status_code == 422:
            error_code = ErrorCode.VALIDATION_ERROR
        elif exc.status_code == 429:
            error_code = ErrorCode.RATE_LIMIT_EXCEEDED
        
        vitruvius_exc = VitruviusException(
            error_code=error_code,
            message=str(exc.detail),
            http_status=exc.status_code
        )
        
        return await vitruvius_exception_handler(request, vitruvius_exc)
    
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle all other exceptions"""
        
        error_id = str(uuid.uuid4())
        
        # Log the full exception with traceback
        logger.error(
            f"Unhandled exception: {type(exc).__name__} - {str(exc)}",
            extra={
                "error_id": error_id,
                "exception_type": type(exc).__name__,
                "path": request.url.path,
                "method": request.method,
                "user_agent": request.headers.get("User-Agent"),
                "client_ip": request.client.host,
                "traceback": traceback.format_exc()
            }
        )
        
        # Create a safe error response
        vitruvius_exc = VitruviusException(
            error_code=ErrorCode.INTERNAL_ERROR,
            message=f"Internal server error: {error_id}",
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        vitruvius_exc.error_id = error_id
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=vitruvius_exc.to_dict()
        )
    
    return {
        VitruviusException: vitruvius_exception_handler,
        HTTPException: http_exception_handler,
        Exception: general_exception_handler
    }


# Helper functions for common error scenarios
def handle_database_error(operation: str, original_error: Exception) -> DatabaseError:
    """Handle database errors consistently"""
    error_id = str(uuid.uuid4())
    
    logger.error(
        f"Database error during {operation}: {str(original_error)}",
        extra={
            "error_id": error_id,
            "operation": operation,
            "exception_type": type(original_error).__name__,
            "traceback": traceback.format_exc()
        }
    )
    
    return DatabaseError(
        message=f"Database operation failed: {operation}",
        details={"error_id": error_id, "operation": operation}
    )


def handle_processing_error(operation: str, original_error: Exception) -> ProcessingError:
    """Handle processing errors consistently"""
    error_id = str(uuid.uuid4())
    
    logger.error(
        f"Processing error during {operation}: {str(original_error)}",
        extra={
            "error_id": error_id,
            "operation": operation,
            "exception_type": type(original_error).__name__,
            "traceback": traceback.format_exc()
        }
    )
    
    return ProcessingError(
        error_code=ErrorCode.PROCESSING_ERROR,
        message=f"Processing failed: {operation}",
        details={"error_id": error_id, "operation": operation}
    )


def handle_file_error(operation: str, original_error: Exception, file_size: Optional[int] = None) -> FileError:
    """Handle file errors consistently"""
    error_id = str(uuid.uuid4())
    
    logger.error(
        f"File error during {operation}: {str(original_error)}",
        extra={
            "error_id": error_id,
            "operation": operation,
            "file_size": file_size,
            "exception_type": type(original_error).__name__,
            "traceback": traceback.format_exc()
        }
    )
    
    # Determine specific error code based on the error
    error_code = ErrorCode.UPLOAD_FAILED
    if "size" in str(original_error).lower():
        error_code = ErrorCode.FILE_TOO_LARGE
    elif "type" in str(original_error).lower() or "format" in str(original_error).lower():
        error_code = ErrorCode.INVALID_FILE_TYPE
    
    return FileError(
        error_code=error_code,
        message=f"File operation failed: {operation}",
        details={"error_id": error_id, "operation": operation, "file_size": file_size}
    )