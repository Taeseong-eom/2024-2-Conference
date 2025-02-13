# 1. Node.js 환경에서 빌드
FROM node:23.6.0 AS builder

WORKDIR /app
COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

# 2. 빌드된 정적 파일을 Nginx로 서빙
FROM nginx:1.21
COPY --from=builder /app/build /usr/share/nginx/html

# Nginx default.conf를 대체하고 싶다면 아래처럼 설정 파일 복사
# COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]