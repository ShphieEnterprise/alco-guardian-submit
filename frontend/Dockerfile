FROM ghcr.io/cirruslabs/flutter:stable AS build

WORKDIR /app

# Copy pubspec to install dependencies first (to leverage Docker cache)
COPY pubspec.* ./
RUN flutter pub get

# Copy the rest of the source code
COPY . .

# Ensure firebase_options.dart is present
RUN ls -la lib/firebase_options.dart || echo "WARNING: firebase_options.dart not found!"

# Ensure web support is enabled and build the web release
RUN flutter config --enable-web \
    && flutter clean \
    && flutter pub get \
    && flutter build web --release --base-href=/

# ------------------------
# Runtime image
# ------------------------
FROM nginx:alpine

# Copy the built web app from the build stage
COPY --from=build /app/build/web /usr/share/nginx/html

# Copy custom nginx configuration for Cloud Run
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Cloud Run listens on port 8080 by default
EXPOSE 8080

# Start Nginx in the foreground
CMD ["nginx", "-g", "daemon off;"]