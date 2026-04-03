#!/bin/bash
set -e

echo "🚀 SQL Query Intelligence Platform: One-Click Verification"
echo "--------------------------------------------------------"

# 1. Dependency Check
if ! command -v docker &> /dev/null
then
    echo "❌ Error: Docker is not installed. Please install it before running."
    exit 1
fi

if ! command -v python3 &> /dev/null
then
    echo "❌ Error: Python 3 is not installed. Required for the demo exporter."
    exit 1
fi

# 2. Boot the Mesh
echo "🏗️  Booting Microservice Mesh (Postgres, Redis, Gateway, Worker)..."
docker-compose up --build -d

echo "⏳ Waiting for stability (10s)..."
sleep 10

# 3. Local Requirements
echo "📦 Installing local dependencies for demo script..."
pip install -r requirements.txt --quiet

# 4. End-to-End Demo
echo "🧪 Running End-to-End Telemetry Test..."
python3 exporters/demo_exporter.py

echo ""
echo "✅ SUCCESS! Platform is fully operational."
echo "--------------------------------------------------------"
echo "👉 Action: Open 'frontend/index.html' in your browser to view the Dashboard."
echo "👉 Logic: All services are now running in the 'query_intel' Docker network."
echo "--------------------------------------------------------"
