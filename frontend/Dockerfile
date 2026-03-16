FROM node:20-alpine AS base

WORKDIR /app
COPY package.json package-lock.json* ./

# Dépendances de développement pour le mode dev
FROM base AS dev
RUN npm install
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev"]
