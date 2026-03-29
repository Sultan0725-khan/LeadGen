#!/bin/bash

# LeadGen Project Start Script
# This script sets up and starts both the Backend and Frontend

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting LeadGen Pipeline Setup...${NC}"

# 0. Cleanup existing processes
echo -e "${GREEN}🧹 Cleaning up existing processes...${NC}"
pkill -f uvicorn > /dev/null 2>&1
pkill -f vite > /dev/null 2>&1
sleep 1

# 1. Backend Setup
echo -e "${GREEN}📦 Setting up Backend...${NC}"
cd backend || exit

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate
echo "Installing backend dependencies..."
pip install -r requirements.txt > /dev/null 2>&1

if [ ! -f ".env" ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo -e "${RED}⚠️  Please edit backend/.env with your API keys!${NC}"
fi

# 2. Frontend Setup
echo -e "${GREEN}📦 Setting up Frontend...${NC}"
cd ../frontend || exit

if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install > /dev/null 2>&1
fi

# 3. Start Both Services
echo -e "${BLUE}✨ Starting Backend and Frontend...${NC}"

# Function to kill background processes on exit
cleanup() {
    echo -e "\n${BLUE}🛑 Stopping services...${NC}"
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit
}

trap cleanup SIGINT

# Start Backend
echo -e "${GREEN}🖥️  Starting Backend on http://localhost:8000${NC}"
cd ../backend || exit
source venv/bin/activate
uvicorn app.main:app --reload > ../backend.log 2>&1 &
BACKEND_PID=$!

# Start Frontend
echo -e "${GREEN}🌐 Starting Frontend on http://localhost:5173${NC}"
cd ../frontend || exit
npm run dev &
FRONTEND_PID=$!

echo -e "${BLUE}✅ Both services are starting!${NC}"
echo -e "Backend logs: tail -f backend.log"
echo -e "Press Ctrl+C to stop both services."

# Wait for background processes
wait $BACKEND_PID $FRONTEND_PID
