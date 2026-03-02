#!/bin/sh

# Frontend Entrypoint Script
# Docker Compose handles dependency management via 'depends_on: condition: service_healthy'
# This script simply starts Next.js

echo "🚀 Starting Gemini InsightLink Frontend..."
exec node_modules/.bin/next start --port 9002
