FROM node:18-alpine AS build
WORKDIR /app

# Install deps first for better caching
COPY package.json ./
RUN npm install --no-audit --no-fund

# Copy source
COPY . .

# Build-time env for Vite
ARG VITE_API_BASE
ARG VITE_STREAMLIT_URL
ARG VITE_STREAMLIT_DOCTOR_URL
ENV VITE_API_BASE=${VITE_API_BASE}
ENV VITE_STREAMLIT_URL=${VITE_STREAMLIT_URL}
ENV VITE_STREAMLIT_DOCTOR_URL=${VITE_STREAMLIT_DOCTOR_URL}

RUN npm run build

FROM nginx:alpine
WORKDIR /usr/share/nginx/html

# SPA-friendly nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist .

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
