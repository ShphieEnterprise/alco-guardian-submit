# Deployment Guide for Alco Guardian Frontend

## Prerequisites

1. **Firebase Configuration**
   - Make sure `lib/firebase_options.dart` exists
   - If not, run: `flutterfire configure`

2. **Google Cloud SDK**
   - Install and authenticate: `gcloud auth login`
   - Set project: `gcloud config set project alco-guardian`

## Deployment Methods

### Method 1: Deploy from Source (Recommended)
```bash
./deploy.sh
```

### Method 2: Deploy using Docker
```bash
./deploy.sh --docker
```

## What the script does

1. **Checks firebase_options.dart exists** - Required for Firebase authentication
2. **Deploys to Cloud Run** - Either from source or Docker image
3. **Shows the service URL** - Where your app is accessible

## Important Files

- `.gitignore` - Excludes `firebase_options.dart` from version control
- `.gcloudignore` - Includes `!lib/firebase_options.dart` to ensure it's deployed
- `.dockerignore` - Includes `!lib/firebase_options.dart` for Docker builds

## Troubleshooting

### Login Error: "configuration-not-found"
1. Check Firebase Authentication is enabled in Firebase Console
2. Verify `firebase_options.dart` has correct API keys
3. Make sure the Web app ID matches your Firebase project

### Deployment fails
1. Check you're authenticated: `gcloud auth list`
2. Verify project: `gcloud config get-value project`
3. Check logs: `gcloud run logs read --service=alco-guardian-frontend`

## Manual Deployment Commands

If you prefer to run commands manually:

```bash
# Option 1: From source
gcloud run deploy alco-guardian-frontend \
  --source . \
  --region asia-northeast1 \
  --platform managed \
  --allow-unauthenticated \
  --project alco-guardian

# Option 2: From Docker
flutter build web --release
docker build -t gcr.io/alco-guardian/alco-guardian-frontend .
docker push gcr.io/alco-guardian/alco-guardian-frontend
gcloud run deploy alco-guardian-frontend \
  --image gcr.io/alco-guardian/alco-guardian-frontend \
  --region asia-northeast1 \
  --platform managed \
  --allow-unauthenticated \
  --project alco-guardian
```