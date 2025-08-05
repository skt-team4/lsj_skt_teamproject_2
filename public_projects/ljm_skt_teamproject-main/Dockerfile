FROM nginx:alpine

# Copy the built web app to nginx html directory
COPY dist /usr/share/nginx/html

# Create nginx config with logging
RUN echo 'server { \
    listen 8080; \
    server_name localhost; \
    root /usr/share/nginx/html; \
    index index.html; \
    \
    # Enable logging \
    access_log /var/log/nginx/access.log; \
    error_log /var/log/nginx/error.log debug; \
    \
    # SPA routing \
    location / { \
        try_files $uri $uri/ /index.html; \
    } \
    \
    # Cache static files \
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|mp4|ttf|woff|woff2|eot)$ { \
        expires 1y; \
        add_header Cache-Control "public, immutable"; \
        add_header Access-Control-Allow-Origin *; \
    } \
}' > /etc/nginx/conf.d/default.conf

# Debug: List directory structure
RUN find /usr/share/nginx/html -type f -name "*.gif" -o -name "*.svg" | head -20

EXPOSE 8080