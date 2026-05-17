# DataArk 前端 Docker 镜像
FROM node:20-alpine AS build

WORKDIR /app
COPY package.json .
RUN npm install
COPY . .
RUN npm run build

# Nginx 运行构建产物
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
