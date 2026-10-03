# Build stage
FROM node:18-alpine as build

WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Install dependencies (will install react-router-dom, axios, tailwind, etc as defined in package.json)
RUN npm install

# Copy project files
COPY . .

# Build the app
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy custom nginx configuration if needed (or just use default and copy build)
COPY --from=build /app/dist /usr/share/nginx/html

# Optional: Add nginx config to support React Router (fallback to index.html)
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
