# Firebase Configuration Guide

## Setting up firebase.json

1. Copy the example file:
   ```bash
   cp firebase.json.example firebase.json
   ```

2. Replace the placeholder values with your actual Firebase project details:
   - `your-project-id`: Your Firebase project ID
   - `YOUR_NUMBER`: Your Firebase app number (found in Firebase console)
   - `YOUR_APP_ID`: Your app-specific ID

3. You can find these values in:
   - Firebase Console → Project Settings → Your Apps
   - Or run `flutterfire configure` to automatically generate this file

## Important Security Notes

- **NEVER** commit `firebase.json` with real credentials to version control
- The file is already added to `.gitignore` to prevent accidental commits
- Each developer should maintain their own local copy
- For CI/CD, use environment variables or secure secret management

## Using FlutterFire CLI

The recommended way to generate this file is using FlutterFire CLI:

```bash
# Install FlutterFire CLI
dart pub global activate flutterfire_cli

# Configure your project
flutterfire configure
```

This will automatically create the `firebase.json` file with correct values.