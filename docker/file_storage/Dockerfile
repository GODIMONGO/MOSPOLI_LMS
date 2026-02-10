FROM nginx:1.29.5

RUN apt-get update \
    && apt-get install -y --no-install-recommends apache2-utils \
    && rm -rf /var/lib/apt/lists/*

COPY docker/file_storage/nginx.conf /etc/nginx/conf.d/default.conf
COPY docker/file_storage/40-generate-htpasswd.sh /docker-entrypoint.d/40-generate-htpasswd.sh

RUN chmod +x /docker-entrypoint.d/40-generate-htpasswd.sh
