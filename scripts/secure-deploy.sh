#!/bin/bash

# Secure deployment script for Vitruvius
# This script updates ECS task definitions to use AWS Secrets Manager
# instead of build-time secrets

set -e

# Configuration
AWS_REGION="us-east-1"
SECRET_NAME="vitruvius-app-secrets"
ECS_CLUSTER="vitruvius-cluster"
BACKEND_SERVICE="vitruvius-backend-service"
WORKER_SERVICE="vitruvius-worker-service"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🔐 Vitruvius Secure Deployment Script${NC}"
echo "======================================"

# Check if AWS CLI is installed and configured
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI is not installed${NC}"
    exit 1
fi

# Check if secrets exist in AWS Secrets Manager
echo -e "${YELLOW}🔍 Checking if secrets exist in AWS Secrets Manager...${NC}"
if aws secretsmanager describe-secret --secret-id "$SECRET_NAME" --region "$AWS_REGION" &> /dev/null; then
    echo -e "${GREEN}✅ Secrets found in AWS Secrets Manager${NC}"
else
    echo -e "${RED}❌ Secrets not found in AWS Secrets Manager${NC}"
    echo "Please create secrets using the following command:"
    echo "aws secretsmanager create-secret --name $SECRET_NAME --description 'Application secrets for Vitruvius' --secret-string '{\"SECRET_KEY\":\"your-secret-key\",\"DATABASE_URL\":\"your-db-url\",\"CELERY_BROKER_URL\":\"your-redis-url\",\"CELERY_RESULT_BACKEND\":\"your-redis-url\"}' --region $AWS_REGION"
    exit 1
fi

# Function to create secure task definition
create_secure_task_definition() {
    local service_name=$1
    local image_name=$2
    local container_port=$3
    local task_family=$4
    
    echo -e "${YELLOW}📝 Creating secure task definition for $service_name...${NC}"
    
    cat > "temp-task-def-$service_name.json" << EOF
{
  "family": "$task_family",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "arn:aws:iam::$ACCOUNT_ID:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::$ACCOUNT_ID:role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "$service_name",
      "image": "$image_name",
      "portMappings": [
        {
          "containerPort": $container_port,
          "protocol": "tcp"
        }
      ],
      "secrets": [
        {
          "name": "SECRET_KEY",
          "valueFrom": "arn:aws:secretsmanager:$AWS_REGION:$ACCOUNT_ID:secret:$SECRET_NAME:SECRET_KEY::"
        },
        {
          "name": "DATABASE_URL",
          "valueFrom": "arn:aws:secretsmanager:$AWS_REGION:$ACCOUNT_ID:secret:$SECRET_NAME:DATABASE_URL::"
        },
        {
          "name": "CELERY_BROKER_URL",
          "valueFrom": "arn:aws:secretsmanager:$AWS_REGION:$ACCOUNT_ID:secret:$SECRET_NAME:CELERY_BROKER_URL::"
        },
        {
          "name": "CELERY_RESULT_BACKEND",
          "valueFrom": "arn:aws:secretsmanager:$AWS_REGION:$ACCOUNT_ID:secret:$SECRET_NAME:CELERY_RESULT_BACKEND::"
        }
      ],
      "environment": [
        {
          "name": "PYTHONPATH",
          "value": "/app"
        },
        {
          "name": "ENVIRONMENT",
          "value": "production"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/$service_name",
          "awslogs-region": "$AWS_REGION",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
EOF
    
    # Register the task definition
    aws ecs register-task-definition \
        --cli-input-json file://temp-task-def-$service_name.json \
        --region $AWS_REGION
    
    # Clean up temporary file
    rm -f temp-task-def-$service_name.json
    
    echo -e "${GREEN}✅ Task definition created for $service_name${NC}"
}

# Function to update ECS service
update_ecs_service() {
    local service_name=$1
    local task_family=$2
    
    echo -e "${YELLOW}🔄 Updating ECS service $service_name...${NC}"
    
    # Get the latest task definition ARN
    TASK_DEF_ARN=$(aws ecs describe-task-definition \
        --task-definition $task_family \
        --region $AWS_REGION \
        --query 'taskDefinition.taskDefinitionArn' \
        --output text)
    
    # Update the service
    aws ecs update-service \
        --cluster $ECS_CLUSTER \
        --service $service_name \
        --task-definition $TASK_DEF_ARN \
        --region $AWS_REGION
    
    echo -e "${GREEN}✅ Service $service_name updated${NC}"
}

# Function to wait for service stability
wait_for_service_stability() {
    local service_name=$1
    
    echo -e "${YELLOW}⏳ Waiting for service $service_name to stabilize...${NC}"
    
    aws ecs wait services-stable \
        --cluster $ECS_CLUSTER \
        --services $service_name \
        --region $AWS_REGION
    
    echo -e "${GREEN}✅ Service $service_name is stable${NC}"
}

# Main deployment process
echo -e "${YELLOW}🚀 Starting secure deployment process...${NC}"

# Get ECR registry URL
ECR_REGISTRY=$(aws ecr describe-registry --region $AWS_REGION --query 'registryId' --output text).dkr.ecr.$AWS_REGION.amazonaws.com

# Get image tag (use latest if not provided)
IMAGE_TAG=${1:-latest}

# Create secure task definitions
create_secure_task_definition "vitruvius-backend" "$ECR_REGISTRY/vitruvius-backend:$IMAGE_TAG" 8000 "vitruvius-backend"
create_secure_task_definition "vitruvius-worker" "$ECR_REGISTRY/vitruvius-worker:$IMAGE_TAG" 8000 "vitruvius-worker"

# Update ECS services
update_ecs_service $BACKEND_SERVICE "vitruvius-backend"
update_ecs_service $WORKER_SERVICE "vitruvius-worker"

# Wait for services to stabilize
wait_for_service_stability $BACKEND_SERVICE
wait_for_service_stability $WORKER_SERVICE

echo -e "${GREEN}🎉 Secure deployment completed successfully!${NC}"
echo ""
echo "Key security improvements:"
echo "✅ Secrets are now stored in AWS Secrets Manager"
echo "✅ No secrets exposed in Docker build history"
echo "✅ Runtime environment variables instead of build-time args"
echo "✅ Proper IAM roles for secret access"
echo ""
echo "Next steps:"
echo "1. Monitor deployment in AWS Console"
echo "2. Verify application functionality"
echo "3. Check CloudWatch logs for any issues"
echo "4. Update CI/CD pipeline to use this secure deployment method"