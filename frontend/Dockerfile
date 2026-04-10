FROM node:20-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

FROM node:20-alpine
WORKDIR /app
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/build ./build
COPY package.json ./

EXPOSE 3000
HEALTHCHECK --interval=15s --timeout=10s --retries=3 CMD wget --quiet --tries=1 --spider http://localhost:3000 || exit 1

CMD ["npm", "start"]
