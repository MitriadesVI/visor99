#!/bin/bash
set -e
cd frontend
npm ci
npm run build
echo "Frontend build complete → frontend/dist/"
