#!/usr/bin/env bash
set -e

# Install backend dependencies
pip install -r backend/requirements.txt

# Build React frontend
cd frontend
npm install
npm run build
cd ..

# Copy built frontend into backend/static for FastAPI to serve
rm -rf backend/static
cp -r frontend/build backend/static
