# Backend Server Status Report

## Summary
The AlcoGuardian backend server is now running successfully on `http://localhost:8080`.

## Server Details
- **Status**: ✅ Running
- **URL**: http://localhost:8080
- **Process**: Running via `simple_local_server.py`
- **Log file**: `server.log`

## Available Endpoints

### 1. Health Check
- **GET** `/health`
- Returns: `{"status": "healthy", "server": "local-test"}`

### 2. Drinks Master Data
- **GET** `/get_drinks_master`
- Returns: List of available drinks with alcohol content and volume

### 3. Bartender Chat
- **POST** `/chat`
- Body: `{"message": "your message"}`
- Returns: Bartender response with message and image ID

### 4. Session Management
- **POST** `/start_session` - Start a new drinking session
- **GET** `/get_current_session` - Get current session info
- **POST** `/add_drink` - Add a drink to current session
  - Body: `{"drink_id": "beer"}`

## Testing the Server

### Quick Test Commands
```bash
# Check if server is running
curl http://localhost:8080/health

# Get drinks list
curl http://localhost:8080/get_drinks_master

# Chat with bartender
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "こんばんは！"}'

# Start a session
curl -X POST http://localhost:8080/start_session

# Add a drink
curl -X POST http://localhost:8080/add_drink \
  -H "Content-Type: application/json" \
  -d '{"drink_id": "beer"}'
```

## Server Management

### Start Server
```bash
uv run python simple_local_server.py
```

### Stop Server
```bash
pkill -f simple_local_server
```

### View Logs
```bash
tail -f server.log
```

## Notes
- The server runs with CORS enabled for all origins
- Authentication is disabled for local testing
- Session data is stored in memory (resets when server restarts)
- Guardian logic provides simple alcohol monitoring based on total consumption

## Troubleshooting

### If server won't start
1. Check if port 8080 is already in use: `lsof -i :8080`
2. Kill any existing processes: `pkill -f simple_local_server`
3. Check Python environment: `uv pip list`

### If endpoints return errors
1. Check server logs: `tail -f server.log`
2. Verify JSON format in POST requests
3. Ensure Content-Type header is set to `application/json`

## Production Deployment
The production backend is deployed as Google Cloud Functions at:
- Project: `YOUR_PROJECT_ID`
- Region: `asia-northeast1`
- Some functions are deployed but may require authentication fixes