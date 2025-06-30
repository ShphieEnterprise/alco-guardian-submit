#!/bin/bash

# Deploy script for Alco Guardian Frontend
# This script builds and deploys the Flutter web app to Cloud Run

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="alco-guardian"
SERVICE_NAME="alco-guardian-frontend"
REGION="asia-northeast1"

echo -e "${GREEN}🚀 Starting deployment process for Alco Guardian Frontend${NC}"

# Check if firebase_options.dart exists
if [ ! -f "lib/firebase_options.dart" ]; then
    echo -e "${RED}❌ Error: lib/firebase_options.dart not found!${NC}"
    echo -e "${YELLOW}Please run 'flutterfire configure' to generate the file${NC}"
    exit 1
fi

# Option 1: Deploy using source (recommended)
deploy_from_source() {
    echo -e "${GREEN}📦 Deploying from source...${NC}"
    
    gcloud run deploy $SERVICE_NAME \
        --source . \
        --region $REGION \
        --platform managed \
        --allow-unauthenticated \
        --project $PROJECT_ID
}

# Option 2: Deploy using Docker image
deploy_from_docker() {
    echo -e "${GREEN}🔨 Building Flutter web app...${NC}"
    flutter build web --release
    
    echo -e "${GREEN}🐳 Building Docker image...${NC}"
    docker build -t gcr.io/$PROJECT_ID/$SERVICE_NAME .
    
    echo -e "${GREEN}📤 Pushing Docker image to Container Registry...${NC}"
    docker push gcr.io/$PROJECT_ID/$SERVICE_NAME
    
    echo -e "${GREEN}🚀 Deploying to Cloud Run...${NC}"
    gcloud run deploy $SERVICE_NAME \
        --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
        --region $REGION \
        --platform managed \
        --allow-unauthenticated \
        --project $PROJECT_ID
}

# Check command line arguments
if [ "$1" == "--docker" ]; then
    deploy_from_docker
else
    deploy_from_source
fi

# Get the service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --project $PROJECT_ID --format 'value(status.url)')

echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
echo -e "${GREEN}🌐 Service URL: $SERVICE_URL${NC}"
echo ""
echo -e "${YELLOW}📝 Note: Make sure to test the login functionality${NC}"