# Unprivileged nginx: runs as a non-root user, listens on 8080, writes only to /tmp.
FROM nginxinc/nginx-unprivileged:1.27-alpine
COPY html /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 8080
