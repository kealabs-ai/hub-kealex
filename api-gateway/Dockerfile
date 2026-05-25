FROM nginx:1.27-alpine

# Copy nginx configurations
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY nginx-ssl.conf /etc/nginx/conf.d/nginx-ssl.conf

# Copy switch script
COPY switch-nginx.sh /usr/local/bin/switch-nginx
RUN chmod +x /usr/local/bin/switch-nginx

# Create health check script
RUN echo '#!/bin/sh\ncurl -f http://localhost/health || exit 1' > /healthcheck.sh && \
    chmod +x /healthcheck.sh

# Ensure nginx runs in foreground
RUN echo 'daemon off;' >> /etc/nginx/nginx.conf

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD /healthcheck.sh