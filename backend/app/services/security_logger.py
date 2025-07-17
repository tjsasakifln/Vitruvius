# Production use requires a separate commercial license from the Licensor.
# For commercial licenses, please contact Tiago Sasaki at tiago@confenge.com.br.

import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass, asdict
from fastapi import Request
import hashlib
import uuid


class SecurityEventType(Enum):
    """Types of security events to log"""
    
    # Authentication events
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    TOKEN_EXPIRED = "token_expired"
    
    # Authorization events
    ACCESS_GRANTED = "access_granted"
    ACCESS_DENIED = "access_denied"
    PERMISSION_ESCALATION = "permission_escalation"
    
    # Rate limiting events
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    RATE_LIMIT_WARNING = "rate_limit_warning"
    
    # File operations
    FILE_UPLOAD_SUCCESS = "file_upload_success"
    FILE_UPLOAD_FAILED = "file_upload_failed"
    FILE_UPLOAD_MALICIOUS = "file_upload_malicious"
    FILE_DOWNLOAD = "file_download"
    FILE_DELETE = "file_delete"
    
    # Data validation
    VALIDATION_FAILED = "validation_failed"
    XSS_ATTEMPT = "xss_attempt"
    SQL_INJECTION_ATTEMPT = "sql_injection_attempt"
    
    # WebSocket events
    WEBSOCKET_CONNECT = "websocket_connect"
    WEBSOCKET_DISCONNECT = "websocket_disconnect"
    WEBSOCKET_MESSAGE_BLOCKED = "websocket_message_blocked"
    
    # System events
    SYSTEM_ERROR = "system_error"
    CONFIGURATION_CHANGE = "configuration_change"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"


class SecurityLevel(Enum):
    """Security event severity levels"""
    
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SecurityEvent:
    """Structured security event"""
    
    event_type: SecurityEventType
    level: SecurityLevel
    message: str
    timestamp: datetime
    event_id: str
    
    # User information
    user_id: Optional[int] = None
    user_email: Optional[str] = None
    user_ip: Optional[str] = None
    user_agent: Optional[str] = None
    
    # Request information
    request_id: Optional[str] = None
    method: Optional[str] = None
    path: Optional[str] = None
    query_params: Optional[Dict[str, Any]] = None
    
    # Additional context
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    action: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    # Risk assessment
    risk_score: Optional[int] = None
    threat_indicators: Optional[list] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging"""
        data = asdict(self)
        # Convert enum values to strings
        data['event_type'] = self.event_type.value
        data['level'] = self.level.value
        data['timestamp'] = self.timestamp.isoformat()
        return data


class SecurityLogger:
    """
    Centralized security logging system
    """
    
    def __init__(self, logger_name: str = "security"):
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(logging.INFO)
        
        # Create console handler if not exists
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def log_security_event(self, event: SecurityEvent):
        """Log a security event"""
        
        # Determine log level based on security level
        log_level = {
            SecurityLevel.LOW: logging.INFO,
            SecurityLevel.MEDIUM: logging.WARNING,
            SecurityLevel.HIGH: logging.ERROR,
            SecurityLevel.CRITICAL: logging.CRITICAL
        }.get(event.level, logging.INFO)
        
        # Create structured log message
        log_data = event.to_dict()
        
        # Log the event
        self.logger.log(
            log_level,
            f"SECURITY_EVENT: {event.event_type.value} - {event.message}",
            extra={
                "security_event": log_data,
                "event_type": event.event_type.value,
                "security_level": event.level.value,
                "event_id": event.event_id
            }
        )
        
        # For critical events, also log as JSON for structured parsing
        if event.level == SecurityLevel.CRITICAL:
            self.logger.critical(
                f"CRITICAL_SECURITY_EVENT: {json.dumps(log_data, indent=2)}"
            )
    
    def log_authentication_event(self, 
                                event_type: SecurityEventType, 
                                user_id: Optional[int] = None,
                                user_email: Optional[str] = None,
                                user_ip: Optional[str] = None,
                                user_agent: Optional[str] = None,
                                message: Optional[str] = None,
                                metadata: Optional[Dict[str, Any]] = None):
        """Log authentication-related events"""
        
        level = SecurityLevel.MEDIUM
        if event_type == SecurityEventType.LOGIN_FAILED:
            level = SecurityLevel.HIGH
        elif event_type == SecurityEventType.LOGIN_SUCCESS:
            level = SecurityLevel.LOW
        
        event = SecurityEvent(
            event_type=event_type,
            level=level,
            message=message or f"Authentication event: {event_type.value}",
            timestamp=datetime.utcnow(),
            event_id=str(uuid.uuid4()),
            user_id=user_id,
            user_email=user_email,
            user_ip=user_ip,
            user_agent=user_agent,
            metadata=metadata
        )
        
        self.log_security_event(event)
    
    def log_authorization_event(self,
                               event_type: SecurityEventType,
                               user_id: int,
                               resource_type: str,
                               resource_id: str,
                               action: str,
                               granted: bool,
                               request: Optional[Request] = None,
                               metadata: Optional[Dict[str, Any]] = None):
        """Log authorization-related events"""
        
        level = SecurityLevel.HIGH if not granted else SecurityLevel.LOW
        
        event = SecurityEvent(
            event_type=event_type,
            level=level,
            message=f"Authorization {'granted' if granted else 'denied'}: {action} on {resource_type}",
            timestamp=datetime.utcnow(),
            event_id=str(uuid.uuid4()),
            user_id=user_id,
            user_ip=request.client.host if request else None,
            user_agent=request.headers.get("User-Agent") if request else None,
            method=request.method if request else None,
            path=request.url.path if request else None,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            metadata=metadata
        )
        
        self.log_security_event(event)
    
    def log_rate_limit_event(self,
                            user_id: Optional[int],
                            user_ip: str,
                            rule_name: str,
                            limit_info: Dict[str, Any],
                            request: Optional[Request] = None):
        """Log rate limiting events"""
        
        event = SecurityEvent(
            event_type=SecurityEventType.RATE_LIMIT_EXCEEDED,
            level=SecurityLevel.MEDIUM,
            message=f"Rate limit exceeded: {rule_name}",
            timestamp=datetime.utcnow(),
            event_id=str(uuid.uuid4()),
            user_id=user_id,
            user_ip=user_ip,
            user_agent=request.headers.get("User-Agent") if request else None,
            method=request.method if request else None,
            path=request.url.path if request else None,
            metadata={
                "rule_name": rule_name,
                "limit_info": limit_info
            }
        )
        
        self.log_security_event(event)
    
    def log_file_event(self,
                      event_type: SecurityEventType,
                      user_id: int,
                      filename: str,
                      file_size: Optional[int] = None,
                      file_type: Optional[str] = None,
                      success: bool = True,
                      error_message: Optional[str] = None,
                      request: Optional[Request] = None,
                      metadata: Optional[Dict[str, Any]] = None):
        """Log file operation events"""
        
        level = SecurityLevel.LOW if success else SecurityLevel.MEDIUM
        if event_type == SecurityEventType.FILE_UPLOAD_MALICIOUS:
            level = SecurityLevel.HIGH
        
        message = f"File operation: {event_type.value} - {filename}"
        if not success and error_message:
            message += f" - Error: {error_message}"
        
        event = SecurityEvent(
            event_type=event_type,
            level=level,
            message=message,
            timestamp=datetime.utcnow(),
            event_id=str(uuid.uuid4()),
            user_id=user_id,
            user_ip=request.client.host if request else None,
            user_agent=request.headers.get("User-Agent") if request else None,
            method=request.method if request else None,
            path=request.url.path if request else None,
            resource_type="file",
            resource_id=filename,
            action=event_type.value,
            metadata={
                "filename": filename,
                "file_size": file_size,
                "file_type": file_type,
                "success": success,
                "error_message": error_message,
                **(metadata or {})
            }
        )
        
        self.log_security_event(event)
    
    def log_validation_event(self,
                           validation_type: str,
                           user_id: Optional[int],
                           input_data: str,
                           validation_error: str,
                           request: Optional[Request] = None):
        """Log validation failure events"""
        
        # Calculate risk score based on validation type
        risk_score = self._calculate_validation_risk(validation_type, input_data)
        
        # Determine if this looks like an attack
        threat_indicators = self._detect_threat_indicators(input_data)
        
        level = SecurityLevel.HIGH if risk_score > 7 else SecurityLevel.MEDIUM
        
        event = SecurityEvent(
            event_type=SecurityEventType.VALIDATION_FAILED,
            level=level,
            message=f"Validation failed: {validation_type} - {validation_error}",
            timestamp=datetime.utcnow(),
            event_id=str(uuid.uuid4()),
            user_id=user_id,
            user_ip=request.client.host if request else None,
            user_agent=request.headers.get("User-Agent") if request else None,
            method=request.method if request else None,
            path=request.url.path if request else None,
            risk_score=risk_score,
            threat_indicators=threat_indicators,
            metadata={
                "validation_type": validation_type,
                "validation_error": validation_error,
                "input_hash": hashlib.sha256(input_data.encode()).hexdigest()[:16]
            }
        )
        
        self.log_security_event(event)
    
    def log_websocket_event(self,
                           event_type: SecurityEventType,
                           user_id: Optional[int],
                           connection_id: str,
                           message: str,
                           metadata: Optional[Dict[str, Any]] = None):
        """Log WebSocket events"""
        
        level = SecurityLevel.LOW
        if event_type == SecurityEventType.WEBSOCKET_MESSAGE_BLOCKED:
            level = SecurityLevel.MEDIUM
        
        event = SecurityEvent(
            event_type=event_type,
            level=level,
            message=message,
            timestamp=datetime.utcnow(),
            event_id=str(uuid.uuid4()),
            user_id=user_id,
            resource_type="websocket",
            resource_id=connection_id,
            metadata=metadata
        )
        
        self.log_security_event(event)
    
    def log_system_event(self,
                        event_type: SecurityEventType,
                        message: str,
                        level: SecurityLevel = SecurityLevel.MEDIUM,
                        metadata: Optional[Dict[str, Any]] = None):
        """Log system-level events"""
        
        event = SecurityEvent(
            event_type=event_type,
            level=level,
            message=message,
            timestamp=datetime.utcnow(),
            event_id=str(uuid.uuid4()),
            metadata=metadata
        )
        
        self.log_security_event(event)
    
    def _calculate_validation_risk(self, validation_type: str, input_data: str) -> int:
        """Calculate risk score for validation failures"""
        
        risk_score = 1
        
        # Check for common attack patterns
        attack_patterns = [
            ('<script', 3),
            ('javascript:', 3),
            ('vbscript:', 3),
            ('onload=', 2),
            ('onerror=', 2),
            ('eval(', 2),
            ('exec(', 2),
            ("'", 1),
            ('"', 1),
            ('<', 1),
            ('>', 1),
            ('union select', 4),
            ('drop table', 4),
            ('insert into', 3),
            ('update set', 3),
            ('delete from', 3),
            ('../', 2),
            ('..\\', 2),
            ('cmd.exe', 3),
            ('powershell', 3),
            ('bash', 2),
            ('sh -c', 2)
        ]
        
        input_lower = input_data.lower()
        
        for pattern, score in attack_patterns:
            if pattern in input_lower:
                risk_score += score
        
        # Length-based risk (very long inputs might be attacks)
        if len(input_data) > 1000:
            risk_score += 2
        elif len(input_data) > 10000:
            risk_score += 4
        
        return min(risk_score, 10)  # Cap at 10
    
    def _detect_threat_indicators(self, input_data: str) -> list:
        """Detect potential threat indicators in input"""
        
        indicators = []
        input_lower = input_data.lower()
        
        # XSS indicators
        xss_indicators = ['<script', 'javascript:', 'vbscript:', 'onload=', 'onerror=', 'onclick=']
        if any(indicator in input_lower for indicator in xss_indicators):
            indicators.append('xss_attempt')
        
        # SQL injection indicators
        sql_indicators = ['union select', 'drop table', 'insert into', 'update set', 'delete from', "'", '"']
        if any(indicator in input_lower for indicator in sql_indicators):
            indicators.append('sql_injection_attempt')
        
        # Path traversal indicators
        path_indicators = ['../', '..\\', '/etc/passwd', '/windows/system32']
        if any(indicator in input_lower for indicator in path_indicators):
            indicators.append('path_traversal_attempt')
        
        # Command injection indicators
        cmd_indicators = ['cmd.exe', 'powershell', 'bash', 'sh -c', '&', '|', ';']
        if any(indicator in input_lower for indicator in cmd_indicators):
            indicators.append('command_injection_attempt')
        
        return indicators


# Global security logger instance
security_logger = SecurityLogger()

# Convenience functions for common security events
def log_login_attempt(user_email: str, success: bool, user_ip: str, user_agent: str, error_message: str = None):
    """Log login attempt"""
    event_type = SecurityEventType.LOGIN_SUCCESS if success else SecurityEventType.LOGIN_FAILED
    message = f"Login {'successful' if success else 'failed'} for {user_email}"
    if not success and error_message:
        message += f": {error_message}"
    
    security_logger.log_authentication_event(
        event_type=event_type,
        user_email=user_email,
        user_ip=user_ip,
        user_agent=user_agent,
        message=message
    )

def log_access_denied(user_id: int, resource_type: str, resource_id: str, action: str, request: Request):
    """Log access denied event"""
    security_logger.log_authorization_event(
        event_type=SecurityEventType.ACCESS_DENIED,
        user_id=user_id,
        resource_type=resource_type,
        resource_id=resource_id,
        action=action,
        granted=False,
        request=request
    )

def log_file_upload(user_id: int, filename: str, file_size: int, success: bool, request: Request, error_message: str = None):
    """Log file upload event"""
    event_type = SecurityEventType.FILE_UPLOAD_SUCCESS if success else SecurityEventType.FILE_UPLOAD_FAILED
    security_logger.log_file_event(
        event_type=event_type,
        user_id=user_id,
        filename=filename,
        file_size=file_size,
        success=success,
        error_message=error_message,
        request=request
    )

def log_validation_failure(validation_type: str, user_id: int, input_data: str, error: str, request: Request):
    """Log validation failure"""
    security_logger.log_validation_event(
        validation_type=validation_type,
        user_id=user_id,
        input_data=input_data,
        validation_error=error,
        request=request
    )