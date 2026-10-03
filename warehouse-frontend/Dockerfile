FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

# Expose Vite dev server port
EXPOSE 5173

# Run Vite with host=0.0.0.0 so it is accessible outside the container
CMD ["npm", "run", "dev", "--", "--host"]
