#!/bin/sh
# Script to switch between nginx configurations

CONFIG_DIR="/etc/nginx/conf.d"
DEFAULT_CONFIG="$CONFIG_DIR/default.conf"
SSL_CONFIG="$CONFIG_DIR/nginx-ssl.conf"
BACKUP_CONFIG="$CONFIG_DIR/default.conf.backup"

case "$1" in
    ssl|SSL)
        echo "Switching to SSL configuration..."
        if [ -f "$SSL_CONFIG" ]; then
            # Backup current config
            cp "$DEFAULT_CONFIG" "$BACKUP_CONFIG"
            # Copy SSL config
            cp "$SSL_CONFIG" "$DEFAULT_CONFIG"
            echo "SSL configuration activated. Restarting nginx..."
            nginx -s reload
            echo "✓ SSL configuration is now active"
        else
            echo "✗ SSL configuration file not found: $SSL_CONFIG"
            exit 1
        fi
        ;;
    normal|default)
        echo "Switching to normal configuration..."
        if [ -f "$BACKUP_CONFIG" ]; then
            # Restore backup
            cp "$BACKUP_CONFIG" "$DEFAULT_CONFIG"
            echo "Normal configuration restored. Restarting nginx..."
            nginx -s reload
            echo "✓ Normal configuration is now active"
        else
            echo "✗ Backup configuration not found. Using default nginx.conf..."
            # If no backup, use the original nginx.conf
            if [ -f "/nginx.conf" ]; then
                cp "/nginx.conf" "$DEFAULT_CONFIG"
                nginx -s reload
                echo "✓ Default configuration restored"
            else
                echo "✗ No configuration files found"
                exit 1
            fi
        fi
        ;;
    test)
        echo "Testing nginx configuration..."
        nginx -t
        if [ $? -eq 0 ]; then
            echo "✓ Nginx configuration test passed"
        else
            echo "✗ Nginx configuration test failed"
            exit 1
        fi
        ;;
    status)
        echo "Current nginx configuration:"
        echo "============================"
        nginx -T 2>/dev/null | head -20
        echo ""
        echo "Active connections:"
        curl -s http://localhost/health 2>/dev/null || echo "Health check failed"
        ;;
    *)
        echo "Usage: $0 {ssl|normal|test|status}"
        echo "  ssl     - Switch to SSL configuration"
        echo "  normal  - Switch to normal configuration"
        echo "  test    - Test nginx configuration"
        echo "  status  - Show current configuration status"
        exit 1
        ;;
esac