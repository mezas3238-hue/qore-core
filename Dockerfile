FROM nginx:1.27-alpine
COPY replay-mobile /usr/share/nginx/html
EXPOSE 80
