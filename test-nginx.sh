#!/bin/bash
# Test script for nginx configuration

echo "Testing nginx configuration..."
echo "=============================="

# Check if nginx is running
if docker ps | grep -q kealex-api-gateway; then
    echo "✓ nginx container is running"
    
    # Test health endpoint
    echo "Testing health endpoint..."
    curl -f http://localhost:8000/health
    if [ $? -eq 0 ]; then
        echo "✓ Health endpoint is working"
    else
        echo "✗ Health endpoint failed"
    fi
    
    # Test CORS headers
    echo "Testing CORS headers..."
    curl -I -X OPTIONS http://localhost:8000/v1/lex/auth 2>/dev/null | grep -i "access-control"
    if [ $? -eq 0 ]; then
        echo "✓ CORS headers are present"
    else
        echo "✗ CORS headers missing"
    fi
    
    # Test redirect for backward compatibility
    echo "Testing backward compatibility redirect..."
    curl -I http://localhost:8000/auth 2>/dev/null | grep -i "301"
    if [ $? -eq 0 ]; then
        echo "✓ Backward compatibility redirect is working"
    else
        echo "✗ Backward compatibility redirect failed"
    fi
    
else
    echo "✗ nginx container is not running"
    echo "Starting containers..."
    docker-compose up -d api-gateway
    sleep 5
    echo "Retrying tests..."
    ./test-nginx.sh
fi

echo ""
echo "Nginx test completed"