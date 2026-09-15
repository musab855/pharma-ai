FROM node:20-slim

WORKDIR /app

COPY package.json ./
RUN npm install

COPY . .

ENV GENERATE_SOURCEMAP=false
ENV ESLINT_NO_DEV_ERRORS=true

EXPOSE 3000

CMD ["npm", "start"]
