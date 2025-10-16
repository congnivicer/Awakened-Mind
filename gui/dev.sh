#!/bin/bash
# Awakened Mind - Development Server Launcher

echo "🚀 Starting Awakened Mind Development Environment"
echo "================================================"
echo ""

# Set PATH to include Node.js
export PATH="/usr/local/bin:$PATH"

# Store the GUI directory
GUI_DIR="/Volumes/NHB_Workspace/awakened_mind/gui"

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down services..."
    kill $API_PID $VITE_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start API server
echo "🔧 Starting API Server (port 3001)..."
cd "$GUI_DIR"
tsx server/index.ts &
API_PID=$!
echo "   API PID: $API_PID"

# Wait a moment for API to start
sleep 2

# Start Vite dev server
echo "🎨 Starting Vite Dev Server (port 5173)..."
vite &
VITE_PID=$!
echo "   Vite PID: $VITE_PID"

echo ""
echo "✅ Both servers running:"
echo "   • Frontend: http://localhost:5173"
echo "   • API:      http://localhost:3001/api"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Wait for both processes
wait
