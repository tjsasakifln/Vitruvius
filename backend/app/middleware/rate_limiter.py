# Production use requires a separate commercial license from the Licensor.
# For commercial licenses, please contact Tiago Sasaki at tiago@confenge.com.br.

import time
import redis
import hashlib
from typing import Dict, Optional, Tuple
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import logging
import json
from datetime import datetime, timedelta
from enum import Enum
from ..services.security_logger import security_logger

logger = logging.getLogger(__name__)


class RateLimitType(Enum):
    """Types of rate limiting strategies"""
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"


class RateLimitRule:
    """Represents a rate limiting rule"""
    
    def __init__(self, 
                 limit: int, 
                 window: int, 
                 rule_type: RateLimitType = RateLimitType.FIXED_WINDOW,
                 burst_limit: Optional[int] = None,
                 description: str = ""):
        self.limit = limit
        self.window = window  # in seconds
        self.rule_type = rule_type
        self.burst_limit = burst_limit or limit
        self.description = description


class RateLimiter:
    """
    Redis-based rate limiter with multiple strategies
    """
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client or self._create_redis_client()
        self.default_rules = {
            # Global rate limits
            "global": RateLimitRule(1000, 60, description="Global requests per minute"),
            
            # Authentication endpoints
            "auth_login": RateLimitRule(5, 60, description="Login attempts per minute"),
            "auth_register": RateLimitRule(3, 300, description="Registration attempts per 5 minutes"),
            
            # File upload endpoints
            "file_upload": RateLimitRule(10, 60, description="File uploads per minute"),
            
            # Project endpoints
            "project_read": RateLimitRule(100, 60, description="Project read operations per minute"),
            "project_write": RateLimitRule(20, 60, description="Project write operations per minute"),
            
            # WebSocket connections
            "websocket_connect": RateLimitRule(10, 60, description="WebSocket connections per minute"),
            
            # Comment and collaboration
            "comment_create": RateLimitRule(30, 60, description="Comments per minute"),
            "collaboration": RateLimitRule(100, 60, description="Collaboration actions per minute"),
        }
    
    def _create_redis_client(self) -> redis.Redis:
        """Create Redis client with fallback"""
        try:
            import os
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/2')
            client = redis.from_url(redis_url, decode_responses=True)
            client.ping()
            return client
        except Exception as e:
            logger.warning(f"Redis unavailable for rate limiting: {e}")
            return None
    
    def get_client_identifier(self, request: Request) -> str:
        """Generate unique client identifier"""
        # Try to get user ID from request if authenticated
        user_id = getattr(request.state, 'user_id', None)
        if user_id:
            return f"user:{user_id}"
        
        # Use IP address with forwarded headers support
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host
        
        # Include user agent to prevent simple IP rotation
        user_agent = request.headers.get("User-Agent", "")
        user_agent_hash = hashlib.md5(user_agent.encode()).hexdigest()[:8]
        
        return f"ip:{client_ip}:{user_agent_hash}"
    
    def get_rate_limit_key(self, client_id: str, rule_name: str, window_start: int) -> str:
        """Generate Redis key for rate limiting"""
        return f"rate_limit:{rule_name}:{client_id}:{window_start}"
    
    def check_rate_limit(self, client_id: str, rule_name: str) -> Tuple[bool, Dict]:
        """
        Check if client is within rate limits
        
        Returns:
            (is_allowed, info_dict)
        """
        if not self.redis_client:
            # If Redis is unavailable, allow requests but log warning
            logger.warning("Rate limiting disabled - Redis unavailable")
            return True, {"status": "disabled", "reason": "redis_unavailable"}
        
        rule = self.default_rules.get(rule_name)
        if not rule:
            logger.warning(f"Unknown rate limit rule: {rule_name}")
            return True, {"status": "unknown_rule"}
        
        try:
            current_time = int(time.time())
            
            if rule.rule_type == RateLimitType.FIXED_WINDOW:
                return self._check_fixed_window(client_id, rule_name, rule, current_time)
            elif rule.rule_type == RateLimitType.SLIDING_WINDOW:
                return self._check_sliding_window(client_id, rule_name, rule, current_time)
            elif rule.rule_type == RateLimitType.TOKEN_BUCKET:
                return self._check_token_bucket(client_id, rule_name, rule, current_time)
            
            return True, {"status": "unknown_type"}
            
        except Exception as e:
            logger.error(f"Rate limiting error: {e}")
            # On error, allow request but log incident
            return True, {"status": "error", "error": str(e)}
    
    def _check_fixed_window(self, client_id: str, rule_name: str, rule: RateLimitRule, current_time: int) -> Tuple[bool, Dict]:
        """Fixed window rate limiting"""
        window_start = (current_time // rule.window) * rule.window
        key = self.get_rate_limit_key(client_id, rule_name, window_start)
        
        try:
            current_count = self.redis_client.get(key)
            current_count = int(current_count) if current_count else 0
            
            if current_count >= rule.limit:
                # Rate limit exceeded
                ttl = self.redis_client.ttl(key)
                return False, {
                    "status": "rate_limited",
                    "limit": rule.limit,
                    "window": rule.window,
                    "current_count": current_count,
                    "reset_time": current_time + (ttl if ttl > 0 else rule.window),
                    "rule_type": rule.rule_type.value
                }
            
            # Increment counter
            pipe = self.redis_client.pipeline()
            pipe.incr(key)
            pipe.expire(key, rule.window)
            pipe.execute()
            
            return True, {
                "status": "allowed",
                "limit": rule.limit,
                "window": rule.window,
                "current_count": current_count + 1,
                "remaining": rule.limit - current_count - 1,
                "reset_time": window_start + rule.window,
                "rule_type": rule.rule_type.value
            }
            
        except Exception as e:
            logger.error(f"Fixed window rate limiting error: {e}")
            return True, {"status": "error", "error": str(e)}
    
    def _check_sliding_window(self, client_id: str, rule_name: str, rule: RateLimitRule, current_time: int) -> Tuple[bool, Dict]:
        """Sliding window rate limiting using sorted sets"""
        key = f"rate_limit_sliding:{rule_name}:{client_id}"
        
        try:
            # Remove old entries outside the window
            cutoff_time = current_time - rule.window
            self.redis_client.zremrangebyscore(key, 0, cutoff_time)
            
            # Count current requests in window
            current_count = self.redis_client.zcard(key)
            
            if current_count >= rule.limit:
                # Rate limit exceeded
                oldest_entry = self.redis_client.zrange(key, 0, 0, withscores=True)
                reset_time = int(oldest_entry[0][1]) + rule.window if oldest_entry else current_time + rule.window
                
                return False, {
                    "status": "rate_limited",
                    "limit": rule.limit,
                    "window": rule.window,
                    "current_count": current_count,
                    "reset_time": reset_time,
                    "rule_type": rule.rule_type.value
                }
            
            # Add current request
            request_id = f"{current_time}:{hashlib.md5(f'{client_id}:{current_time}'.encode()).hexdigest()[:8]}"
            self.redis_client.zadd(key, {request_id: current_time})
            self.redis_client.expire(key, rule.window)
            
            return True, {
                "status": "allowed",
                "limit": rule.limit,
                "window": rule.window,
                "current_count": current_count + 1,
                "remaining": rule.limit - current_count - 1,
                "rule_type": rule.rule_type.value
            }
            
        except Exception as e:
            logger.error(f"Sliding window rate limiting error: {e}")
            return True, {"status": "error", "error": str(e)}
    
    def _check_token_bucket(self, client_id: str, rule_name: str, rule: RateLimitRule, current_time: int) -> Tuple[bool, Dict]:
        """Token bucket rate limiting"""
        key = f"rate_limit_bucket:{rule_name}:{client_id}"
        
        try:
            bucket_data = self.redis_client.hgetall(key)
            
            if bucket_data:
                last_refill = float(bucket_data.get('last_refill', current_time))
                tokens = float(bucket_data.get('tokens', rule.limit))
            else:
                last_refill = current_time
                tokens = rule.limit
            
            # Calculate tokens to add based on time elapsed
            time_elapsed = current_time - last_refill
            tokens_to_add = (time_elapsed / rule.window) * rule.limit
            tokens = min(rule.burst_limit, tokens + tokens_to_add)
            
            if tokens < 1:
                # No tokens available
                return False, {
                    "status": "rate_limited",
                    "limit": rule.limit,
                    "window": rule.window,
                    "tokens": tokens,
                    "rule_type": rule.rule_type.value
                }
            
            # Consume one token
            tokens -= 1
            
            # Update bucket
            self.redis_client.hset(key, mapping={
                'tokens': tokens,
                'last_refill': current_time
            })
            self.redis_client.expire(key, rule.window * 2)  # Keep bucket alive longer
            
            return True, {
                "status": "allowed",
                "limit": rule.limit,
                "window": rule.window,
                "tokens": tokens,
                "rule_type": rule.rule_type.value
            }
            
        except Exception as e:
            logger.error(f"Token bucket rate limiting error: {e}")
            return True, {"status": "error", "error": str(e)}
    
    def get_rate_limit_info(self, client_id: str, rule_name: str) -> Dict:
        """Get current rate limit status without consuming quota"""
        if not self.redis_client:
            return {"status": "disabled"}
        
        rule = self.default_rules.get(rule_name)
        if not rule:
            return {"status": "unknown_rule"}
        
        try:
            current_time = int(time.time())
            
            if rule.rule_type == RateLimitType.FIXED_WINDOW:
                window_start = (current_time // rule.window) * rule.window
                key = self.get_rate_limit_key(client_id, rule_name, window_start)
                current_count = int(self.redis_client.get(key) or 0)
                
                return {
                    "limit": rule.limit,
                    "window": rule.window,
                    "current_count": current_count,
                    "remaining": rule.limit - current_count,
                    "reset_time": window_start + rule.window,
                    "rule_type": rule.rule_type.value
                }
            
            # Similar implementations for other types...
            return {"status": "not_implemented"}
            
        except Exception as e:
            logger.error(f"Rate limit info error: {e}")
            return {"status": "error", "error": str(e)}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for rate limiting
    """
    
    def __init__(self, app: ASGIApp, rate_limiter: Optional[RateLimiter] = None):
        super().__init__(app)
        self.rate_limiter = rate_limiter or RateLimiter()
        
        # Define route patterns and their rate limit rules
        self.route_rules = {
            # Authentication endpoints
            r"/api/v1/auth/login": "auth_login",
            r"/api/v1/auth/token": "auth_login",
            r"/api/v1/auth/register": "auth_register",
            
            # File upload endpoints
            r"/api/v1/projects/\d+/upload-ifc": "file_upload",
            
            # Project write operations
            r"/api/v1/projects/\d+/conflicts": "project_write",
            r"/api/v1/projects": "project_write",
            
            # WebSocket connections
            r"/api/v1/collaboration/ws": "websocket_connect",
            
            # Comment endpoints
            r"/api/v1/collaboration/conflicts/\d+/comments": "comment_create",
        }
    
    async def dispatch(self, request: Request, call_next):
        """Process rate limiting for incoming requests"""
        
        # Skip rate limiting for health checks and static files
        if request.url.path in ["/health", "/metrics", "/favicon.ico"]:
            return await call_next(request)
        
        # Skip for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # Determine rate limit rule
        rule_name = self._get_rule_for_path(request.url.path, request.method)
        
        if not rule_name:
            # No specific rule, use global rate limiting
            rule_name = "global"
        
        # Get client identifier
        client_id = self.rate_limiter.get_client_identifier(request)
        
        # Check rate limit
        is_allowed, rate_info = self.rate_limiter.check_rate_limit(client_id, rule_name)
        
        if not is_allowed:
            # Rate limit exceeded
            logger.warning(f"Rate limit exceeded for client {client_id} on rule {rule_name}: {rate_info}")
            
            # Log security event
            user_id = getattr(request.state, 'user_id', None)
            user_ip = request.client.host if request.client else None
            
            security_logger.log_rate_limit_event(
                user_id=user_id,
                user_ip=user_ip,
                rule_name=rule_name,
                limit_info=rate_info,
                request=request
            )
            
            # Add security event to request state for audit logging
            request.state.security_event = {
                "type": "rate_limit_exceeded",
                "client_id": client_id,
                "rule": rule_name,
                "path": request.url.path,
                "method": request.method,
                "rate_info": rate_info
            }
            
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "message": "Too many requests. Please try again later.",
                    "retry_after": rate_info.get("reset_time", 0) - int(time.time())
                },
                headers={
                    "X-RateLimit-Limit": str(rate_info.get("limit", 0)),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(rate_info.get("reset_time", 0)),
                    "Retry-After": str(rate_info.get("reset_time", 0) - int(time.time()))
                }
            )
        
        # Add rate limit info to response headers
        response = await call_next(request)
        
        if rate_info.get("status") == "allowed":
            response.headers["X-RateLimit-Limit"] = str(rate_info.get("limit", 0))
            response.headers["X-RateLimit-Remaining"] = str(rate_info.get("remaining", 0))
            response.headers["X-RateLimit-Reset"] = str(rate_info.get("reset_time", 0))
        
        return response
    
    def _get_rule_for_path(self, path: str, method: str) -> Optional[str]:
        """Determine which rate limiting rule applies to a path"""
        import re
        
        for pattern, rule_name in self.route_rules.items():
            if re.match(pattern, path):
                return rule_name
        
        # Default rules based on method
        if method in ["POST", "PUT", "DELETE"]:
            return "project_write"
        elif method == "GET":
            return "project_read"
        
        return None


# Factory function to create rate limiter instance
def create_rate_limiter() -> RateLimiter:
    """Create a configured RateLimiter instance"""
    return RateLimiter()


# Factory function to create rate limiting middleware
def create_rate_limit_middleware(app: ASGIApp) -> RateLimitMiddleware:
    """Create rate limiting middleware with configured rate limiter"""
    return RateLimitMiddleware(app, create_rate_limiter())