# I-CARE React (Vite dev server for demos)
FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .

EXPOSE 3000

ENV VITE_API_BASE_URL=http://localhost:8000

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3000"]
