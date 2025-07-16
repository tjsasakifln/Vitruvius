# Autodesk Platform Services (APS) Integration

This integration connects Vitruvius directly with Autodesk Platform Services (formerly Forge), enabling seamless access to BIM 360 and Autodesk Construction Cloud projects.

## Features

### 1. OAuth2 Authentication
- Secure 3-legged OAuth2 flow with Autodesk
- Automatic token refresh
- User profile integration

### 2. Data Management API
- Browse hubs, projects, and folders
- Access project files and versions
- Navigate BIM 360/ACC project structure

### 3. Model Derivative API
- Translate Revit models to IFC format
- Download processed models for Vitruvius analysis
- Support for multiple model formats

### 4. Issues API
- Create issues in BIM 360/ACC from detected clashes
- Automatic 3D positioning with pushpins
- Bidirectional synchronization of issue status

## Setup Instructions

### 1. APS App Registration

1. **Create APS App**:
   - Go to [Autodesk Developer Portal](https://developer.autodesk.com)
   - Create a new app
   - Select "BIM 360 API", "Data Management API", "Model Derivative API"
   - Note down your Client ID and Client Secret

2. **Configure Callback URL**:
   - Add `http://localhost:8000/api/v1/aps/callback` for development
   - Add your production URL for deployment

### 2. Environment Configuration

Add the following environment variables to your `.env` file:

```bash
# APS Configuration
APS_CLIENT_ID=your_client_id_here
APS_CLIENT_SECRET=your_client_secret_here
APS_CALLBACK_URL=http://localhost:8000/api/v1/aps/callback

# Optional: APS Environment (default: PRODUCTION)
APS_ENVIRONMENT=PRODUCTION
```

### 3. Database Updates

Run database migrations to add APS-related fields:

```sql
-- Add APS integration fields to projects table
ALTER TABLE projects ADD COLUMN aps_project_id VARCHAR(255);
ALTER TABLE projects ADD COLUMN aps_hub_id VARCHAR(255);

-- Add APS issue ID to conflicts table
ALTER TABLE conflicts ADD COLUMN aps_issue_id VARCHAR(255);
```

### 4. Backend Dependencies

Install required Python packages:

```bash
pip install requests authlib
```

### 5. Frontend Integration

Add the APS integration component to your React app:

```jsx
import APSIntegration from './components/APSIntegration';

// In your main app component
<APSIntegration />
```

## Usage Workflow

### 1. Authentication
1. User clicks "Connect to APS"
2. Redirected to Autodesk login
3. User authorizes Vitruvius app
4. Callback handler stores tokens

### 2. Project Selection
1. Browse available hubs (teams/companies)
2. Select a project
3. Navigate through project folders
4. Choose models to process

### 3. Model Processing
1. Click "Process in Vitruvius" on any model
2. Model is translated to IFC format
3. IFC is downloaded and processed
4. Clash detection runs automatically

### 4. Issue Creation
1. View clash detection results
2. Click "Create Issue" for any clash
3. Issue is created in BIM 360/ACC
4. 3D location is automatically set

## API Endpoints

### Authentication
- `GET /api/v1/aps/auth/login` - Initiate OAuth2 flow
- `GET /api/v1/aps/auth/callback` - Handle OAuth2 callback

### Data Management
- `GET /api/v1/aps/hubs` - List accessible hubs
- `GET /api/v1/aps/hubs/{hub_id}/projects` - List projects in hub
- `GET /api/v1/aps/projects/{project_id}/contents` - Browse project contents

### Model Processing
- `POST /api/v1/aps/projects/{project_id}/items/{item_id}/process` - Process model

### Issues Management
- `POST /api/v1/aps/projects/{project_id}/conflicts/{conflict_id}/create-issue` - Create issue
- `GET /api/v1/aps/projects/{project_id}/issues` - List issues

## Configuration Options

### Scopes
The integration requests the following APS scopes:
- `data:read` - Read project data
- `data:write` - Write project data
- `data:create` - Create new data
- `data:search` - Search project data
- `account:read` - Read account information
- `user-profile:read` - Read user profile

### Translation Options
IFC translation can be configured with:
- Export file structure (single/multiple)
- Export settings (standard/custom)
- Include/exclude specific elements

## Security Considerations

### Token Storage
- Access tokens are stored securely in the backend
- Refresh tokens are encrypted
- Tokens are scoped to specific users

### API Rate Limits
- APS has rate limits (100 requests/minute)
- Implement exponential backoff for failed requests
- Cache frequently accessed data

### Error Handling
- Graceful handling of expired tokens
- Automatic token refresh
- User-friendly error messages

## Troubleshooting

### Common Issues

1. **"APS integration not configured"**
   - Check APS_CLIENT_ID and APS_CLIENT_SECRET environment variables
   - Verify app registration in Autodesk Developer Portal

2. **"Authentication failed"**
   - Check callback URL configuration
   - Verify app has correct permissions
   - Ensure user has access to BIM 360/ACC

3. **"Translation failed"**
   - Check file format is supported
   - Verify file is not corrupted
   - Check APS service status

4. **"Token expired"**
   - Automatic refresh should handle this
   - Re-authenticate if refresh fails
   - Check token storage implementation

### Debug Mode

Enable debug logging:

```python
import logging
logging.getLogger('aps_integration').setLevel(logging.DEBUG)
```

### Rate Limiting

Monitor API usage:

```python
# Check rate limit headers
response.headers.get('X-RateLimit-Remaining')
response.headers.get('X-RateLimit-Reset')
```

## Development Notes

### Testing
- Use APS staging environment for testing
- Mock APS responses for unit tests
- Test with different file formats and sizes

### Performance
- Implement caching for frequently accessed data
- Use async processing for long-running operations
- Monitor translation job progress

### Scalability
- Consider token storage at scale
- Implement proper error recovery
- Use queues for background processing

## Support

For issues with the APS integration:
1. Check the [APS Documentation](https://forge.autodesk.com/en/docs/)
2. Review the [APS Forums](https://forge.autodesk.com/categories)
3. Contact the Vitruvius development team

## License

This integration is part of the Vitruvius project and follows the same license terms.