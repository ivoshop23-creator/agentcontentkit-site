FROM nginx:1.27-alpine
RUN apk add --no-cache python3
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY api/ /app/
COPY start.sh /start.sh
COPY site/ /usr/share/nginx/html/
RUN chmod +x /start.sh && mkdir -p /data
VOLUME /data
EXPOSE 80
CMD ["/start.sh"]
