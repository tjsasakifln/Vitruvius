# Vitruvius - Security Documentation

## 🔐 Critical Security Vulnerabilities - RESOLVED

This document outlines the security vulnerabilities that were identified and fixed in the Vitruvius project.

### 1. Remote Code Execution (RCE) via Pickle Deserialization - CRITICAL ✅ FIXED

**Issue**: Celery tasks used pickle for serializing/deserializing cache data, allowing arbitrary code execution if Redis is compromised.

**Location**: `backend/app/tasks/process_ifc.py`

**Fix**: 
- Removed all pickle imports and usage
- Implemented secure JSON serialization with helper functions
- Added proper data type conversion for complex objects
- Maintained cache performance and compatibility

**Impact**: Prevented potential remote code execution attacks through cache poisoning.

### 2. WebSocket Message Validation Bypass - CRITICAL ✅ FIXED

**Issue**: Insufficient validation of WebSocket messages could lead to DoS attacks and logic bypass.

**Location**: `backend/app/api/v1/endpoints/collaboration.py`

**Fix**:
- Added strict message size limits (1MB max)
- Implemented message type whitelist validation
- Enhanced Pydantic schemas with proper validators
- Improved error handling and logging

**Impact**: Prevented DoS attacks and unauthorized message processing.

### 3. Unsafe IFC File Processing - HIGH ✅ FIXED

**Issue**: IFC files were processed without proper content validation, allowing malicious files to potentially exploit processing libraries.

**Location**: `backend/app/api/v1/endpoints/projects.py`

**Fix**:
- Reduced file size limit from 100MB to 50MB
- Added comprehensive content validation function
- Implemented suspicious pattern detection
- Enhanced file structure validation

**Impact**: Prevented upload and processing of malicious files disguised as IFC.

### 4. Lack of Resource Limits - MEDIUM ✅ FIXED

**Issue**: No resource limits during IFC processing could lead to resource exhaustion attacks.

**Location**: `backend/app/services/sandbox_processor.py` (new)

**Fix**:
- Created sandboxed processing environment
- Implemented memory limits (512MB)
- Added CPU time limits (300 seconds)
- Isolated processing in separate processes
- Added timeout and forced termination

**Impact**: Prevented resource exhaustion and improved system stability.

## 🛡️ Security Testing Guide

### Testing Pickle Deserialization Fix

```python
# Verify no pickle imports remain
import ast
import os

def check_no_pickle_imports(file_path):
    with open(file_path, 'r') as f:
        tree = ast.parse(f.read())
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name != 'pickle'
        elif isinstance(node, ast.ImportFrom):
            assert node.module != 'pickle'

# Test JSON serialization works
from backend.app.tasks.process_ifc import serialize_for_cache
import json

test_data = {"elements": [{"id": 1, "name": "test"}]}
serialized = serialize_for_cache(test_data)
json_str = json.dumps(serialized)
assert json.loads(json_str) == serialized
```

### Testing WebSocket Validation

```python
# Test message size validation
large_message = json.dumps({"type": "test", "data": "x" * (1024 * 1024 + 1)})
# Should be rejected with "Message too large" error

# Test invalid message type
invalid_message = json.dumps({"type": "invalid_type", "data": {}})
# Should be rejected with validation error

# Test valid message
valid_message = json.dumps({"type": "ping"})
# Should be accepted
```

### Testing IFC File Security

```python
from backend.app.api.v1.endpoints.projects import validate_ifc_content

# Test invalid file
invalid_file = b"NOT_IFC_FILE"
assert not validate_ifc_content(invalid_file)

# Test suspicious content
malicious_ifc = b"""ISO-10303-21;
HEADER;
FILE_DESCRIPTION ((''), '2;1');
ENDSEC;
DATA;
#1=IFCPROJECT('test','test','<script>alert("xss")</script>',$,$,'test',$,$,$);
ENDSEC;
"""
assert not validate_ifc_content(malicious_ifc)
```

## 🔒 Security Configuration

### Environment Variables
```bash
# File upload limits
MAX_FILE_SIZE=52428800  # 50MB
MAX_WEBSOCKET_MESSAGE_SIZE=1048576  # 1MB

# Processing limits
SANDBOX_MEMORY_LIMIT=536870912  # 512MB
SANDBOX_CPU_TIME_LIMIT=300  # 5 minutes
```

### Production Security Recommendations

1. **File Processing**:
   - Run IFC processing in isolated containers
   - Implement file quarantine system
   - Regular security audits of processing libraries

2. **Network Security**:
   - Use HTTPS for all communications
   - Implement rate limiting on endpoints
   - Monitor for unusual traffic patterns

3. **Database Security**:
   - Use separate Redis instance for caching
   - Encrypt sensitive data at rest
   - Regular backup and recovery testing

4. **Monitoring & Logging**:
   - Log all security events
   - Monitor failed validation attempts
   - Set up alerts for suspicious activities

## 🚨 Security Incident Response

If you discover a security vulnerability:

1. **DO NOT** open a public issue
2. Email: security@vitruvius.com
3. Include detailed reproduction steps
4. Allow time for assessment and fix
5. Coordinate disclosure timeline

### 5. Role-Based Access Control (RBAC) Implementation - HIGH ✅ FIXED

**Issue**: Project access control was based only on owner_id, insufficient for collaborative environments.

**Location**: `backend/app/db/models/rbac.py` (new), `backend/app/services/rbac_service.py` (new)

**Fix**:
- Created comprehensive RBAC system with roles and permissions
- Implemented project-level permission checking
- Added audit logging for security events
- Created role assignment and invitation system
- Updated API endpoints to use permission-based access control

**Impact**: Proper access control for collaborative projects with detailed permission management.

### 6. Secure API Key Management for Revit Add-in - HIGH ✅ FIXED

**Issue**: API keys stored in plain text in configuration files.

**Location**: `revit-addin/VitruviusRevitAddin/`

**Fix**:
- Removed plain text API key storage
- Implemented secure authentication using JWT tokens
- Added Windows Credential Manager integration
- Created SecureAuthManager class for secure credential handling
- Added automatic token refresh mechanism

**Impact**: Eliminated API key exposure and implemented secure authentication flow.

### 7. CI/CD Pipeline Secret Leakage Prevention - HIGH ✅ FIXED

**Issue**: Secrets passed as build arguments could leak in Docker history.

**Location**: `.github/workflows/ci-cd.yml`, `scripts/secure-deploy.sh` (new)

**Fix**:
- Removed build-time secret injection
- Implemented AWS Secrets Manager integration
- Created secure deployment script
- Updated ECS task definitions to use runtime secrets
- Added proper IAM roles for secret access

**Impact**: Prevented secret leakage in Docker builds and improved secret management.

### 8. Authentication Schema Standardization - MEDIUM ✅ FIXED

**Issue**: Inconsistent authentication schemas across endpoints.

**Location**: `backend/app/api/v1/endpoints/auth.py`

**Fix**:
- Added standardized LoginRequest schema
- Created both OAuth2 and JSON login endpoints
- Maintained backward compatibility
- Enhanced error handling consistency

**Impact**: Improved API consistency and developer experience.

## 📋 Security Checklist

- [x] Removed pickle deserialization
- [x] Implemented WebSocket validation
- [x] Added file content validation
- [x] Created sandboxed processing
- [x] Added resource limits
- [x] Enhanced error handling
- [x] Improved logging
- [x] Created security documentation
- [x] Added security tests
- [x] Implemented RBAC system
- [x] Secured API key management
- [x] Fixed CI/CD secret leakage
- [x] Standardized authentication schemas

## 🔄 Regular Security Tasks

### Monthly
- Review and update dependencies
- Check for new security advisories
- Rotate API keys and secrets
- Review access logs

### Quarterly
- Conduct security assessment
- Update security documentation
- Review and test incident response plan
- Security awareness training

### GitHub Secrets Required

For CI/CD pipeline security:
- `AWS_ACCESS_KEY_ID` - AWS access key
- `AWS_SECRET_ACCESS_KEY` - AWS secret key
- `SECRET_KEY` - JWT secret (min 32 chars)
- `DATABASE_URL` - Database connection
- `CELERY_BROKER_URL` - Redis broker URL
- `CELERY_RESULT_BACKEND` - Redis backend URL

Generate secure SECRET_KEY:
```python
import secrets
print(secrets.token_urlsafe(32))
```

## 📊 Security Metrics

Track these metrics:
- File upload rejection rate
- WebSocket message validation failures
- Processing timeout events
- Resource limit violations
- Cache hit rates

Last updated: 2025-01-17