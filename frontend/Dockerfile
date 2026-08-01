FROM node:22-alpine

WORKDIR /app
ARG NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
COPY package.json ./
RUN npm install
COPY . ./
RUN npm run build
RUN cp -r .next/static .next/standalone/.next/static
EXPOSE 3000
CMD ["node", ".next/standalone/server.js"]
