#!/bin/bash

# Production use requires a separate commercial license from the Licensor.
# For commercial licenses, please contact Tiago Sasaki at tiago@confenge.com.br.

# Deployment script with proper image tag management
# Usage: ./deploy-with-tags.sh [IMAGE_TAG] [ENVIRONMENT]

set -e

IMAGE_TAG=${1:-$(git rev-parse HEAD)}
ENVIRONMENT=${2:-production}

echo "🚀 Deploying Vitruvius with tag: $IMAGE_TAG to environment: $ENVIRONMENT"

# Validate that the image tag is not 'latest'
if [[ "$IMAGE_TAG" == "latest" ]]; then
    echo "❌ Error: Using 'latest' tag is not allowed in production deployments"
    echo "Please specify a specific commit SHA or version tag"
    exit 1
fi

# Validate that the image tag exists
ECR_REGISTRY=$(aws sts get-caller-identity --query Account --output text).dkr.ecr.us-east-1.amazonaws.com

echo "🔍 Validating image tags exist in ECR..."
for repo in vitruvius-backend vitruvius-worker vitruvius-frontend; do
    echo "Checking $repo:$IMAGE_TAG..."
    if ! aws ecr describe-images --repository-name $repo --image-ids imageTag=$IMAGE_TAG > /dev/null 2>&1; then
        echo "❌ Error: Image $repo:$IMAGE_TAG not found in ECR"
        exit 1
    fi
done

echo "✅ All image tags validated successfully"

# Set environment variables
export ECR_REGISTRY
export IMAGE_TAG
export ENVIRONMENT

# Load environment-specific variables
if [[ -f ".env.$ENVIRONMENT" ]]; then
    echo "📁 Loading environment variables from .env.$ENVIRONMENT"
    export $(cat .env.$ENVIRONMENT | xargs)
else
    echo "⚠️  Warning: No .env.$ENVIRONMENT file found"
fi

# Deploy using docker-compose
echo "🔄 Starting deployment..."
docker-compose -f docker-compose.prod.yml down --remove-orphans
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d

# Wait for services to be healthy
echo "🏥 Waiting for services to be healthy..."
timeout=300
elapsed=0
while [[ $elapsed -lt $timeout ]]; do
    if docker-compose -f docker-compose.prod.yml ps | grep -q "healthy"; then
        echo "✅ Services are healthy"
        break
    fi
    sleep 5
    elapsed=$((elapsed + 5))
done

if [[ $elapsed -ge $timeout ]]; then
    echo "❌ Timeout waiting for services to be healthy"
    docker-compose -f docker-compose.prod.yml logs
    exit 1
fi

# Run database migrations
echo "🗄️  Running database migrations..."
docker-compose -f docker-compose.prod.yml exec backend python -m app.db.init_db

# Verify deployment
echo "🔍 Verifying deployment..."
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Backend health check passed"
else
    echo "❌ Backend health check failed"
    exit 1
fi

if curl -f http://localhost:3000/health > /dev/null 2>&1; then
    echo "✅ Frontend health check passed"
else
    echo "❌ Frontend health check failed"
    exit 1
fi

echo "🎉 Deployment completed successfully!"
echo "📊 Deployment details:"
echo "  - Image Tag: $IMAGE_TAG"
echo "  - Environment: $ENVIRONMENT"
echo "  - Backend: http://localhost:8000"
echo "  - Frontend: http://localhost:3000"
echo "  - Deployed at: $(date)"

# Log deployment for audit trail
echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") - Deployed $IMAGE_TAG to $ENVIRONMENT" >> deployment.log