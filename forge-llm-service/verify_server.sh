#!/bin/bash

# Script to verify if the LLM server is running and check basic connectivity
# Helps troubleshoot connectivity issues between Java and the Flask server

# Exit on error
set -e

# Default endpoint
LLM_ENDPOINT="http://localhost:7861"

# Process command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --endpoint)
            LLM_ENDPOINT="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--endpoint URL]"
            exit 1
            ;;
    esac
done

echo "======================================================="
echo "LLM SERVER VERIFICATION"
echo "======================================================="
echo "Target endpoint: $LLM_ENDPOINT"
echo

# Extract host and port from endpoint
ENDPOINT_HOST=$(echo $LLM_ENDPOINT | sed -E 's|https?://||' | sed -E 's|:[0-9]+/?.*||')
ENDPOINT_PORT=$(echo $LLM_ENDPOINT | grep -oE ':[0-9]+' | tr -d ':')
if [[ -z "$ENDPOINT_PORT" ]]; then
    if [[ $LLM_ENDPOINT == https://* ]]; then
        ENDPOINT_PORT=443
    else
        ENDPOINT_PORT=80
    fi
fi

# Display environment info
echo "======================================================="
echo "ENVIRONMENT INFORMATION"
echo "======================================================="
echo "Operating system: $(uname -a)"
echo "Network configuration:"
ifconfig | grep -E 'inet|lo|eth' || ip addr | grep -E 'inet|lo|eth'
echo
echo "Host: $ENDPOINT_HOST"
echo "Port: $ENDPOINT_PORT"
echo

# Check if server is running
echo "======================================================="
echo "CHECKING SERVER STATUS"
echo "======================================================="
if [[ "$ENDPOINT_HOST" == "localhost" || "$ENDPOINT_HOST" == "127.0.0.1" ]]; then
    echo "Checking for local process listening on port $ENDPOINT_PORT..."
    lsof -i :$ENDPOINT_PORT || echo "No process found listening on port $ENDPOINT_PORT"
    echo
    echo "Checking for Python processes..."
    ps aux | grep -E "python.*server" | grep -v grep || echo "No Python server processes found"
fi
echo

# Network connectivity test
echo "======================================================="
echo "NETWORK CONNECTIVITY TEST"
echo "======================================================="
echo "Testing network connectivity to $ENDPOINT_HOST:$ENDPOINT_PORT..."
nc -zv $ENDPOINT_HOST $ENDPOINT_PORT -w 5 || echo "Connection test failed"
echo

# Curl tests
echo "======================================================="
echo "CURL HTTP TESTS"
echo "======================================================="
echo "Testing GET request to $LLM_ENDPOINT..."
curl -v $LLM_ENDPOINT
echo
echo "Testing POST request to $LLM_ENDPOINT/act..."
curl -v -X POST -H "Content-Type: application/json" -d '{"context":"debug","message":"test"}' "$LLM_ENDPOINT/act"
echo

echo "======================================================="
echo "SERVER VERIFICATION COMPLETE"
echo "======================================================="