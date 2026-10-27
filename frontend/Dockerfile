FROM node:24.22.1-alpine
WORKDIR /ui
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
EXPOSE 5173
CMD ["npm", "run", "dev"]
