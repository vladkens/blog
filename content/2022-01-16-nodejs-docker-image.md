---
title: How to reduce NodeJS Docker Image Size?
slug: small-nodejs-docker-image
date: 2022-01-16
taxonomies:
  tags: ["docker", "nodejs"]
extra:
  medium: https://medium.com/p/dc5c8999cd96
---

Hi. Today I want to talk about how to reduce the size of the Docker Image with NodeJS inside.

In my company project we use NodeJS as a backend of one of the services. I noticed that there is a big delay between when the project is built in CI and when the new version of the service actually starts working.

I started researching this topic and noticed that the NodeJS Docker Image size takes up 1.3Gb of space. So on each deploy these data first uploaded to registry and then downloaded back to run in Kubernetes cluster.

To check the size of your Docker need to run few commands:

```sh
> docker build -t app .
> docker images | grep app
app     latest    62dec8181ae0   30 seconds ago   1.28GB
```

Well, let’s fix that problem.

## Smaller Docker Base Image

The most basic and simple solution would be to change the basic Docker Image to the alpine version. To do this, change in the first line of the Dockerfile `FROM node:16` to `FROM node:16-alpine`. This was already in my Dockerfile, so this optimization won’t help me. The original Docker file looks like:

```yaml
FROM node:16-alpine

WORKDIR /app
COPY . .

RUN yarn install
RUN yarn app:build

EXPOSE 3000
CMD node dist/app.js
```

## Multi-Stage Builds

The process of creating a Docker container can be divided into several steps, where different parts of the application are prepared individually. And then the necessary files from the intermediate stages can be copied into the final image.

This makes sense, because during the build a lot of temporary files are created, there are dev dependencies in package.json and other things that are not really needed for the final application to work.

I divided the build process of container into three steps. The first step builds the application (compiling the TypeScript, validation schemes, etc.). The second stage installs only those dependencies that are needed for the production of the application. Finally, the third stage copies the compiled application from the first stage and the dependencies from the second stage and runs the application.

This approach requires a little more time to build the container, but it also reduces its size considerably. For example, the TypeScript dependency alone takes up over 80 mb of space. The final Dockerfile looks like:

```yaml
FROM node:16-alpine as dist
WORKDIR /app
COPY . .
RUN yarn install
RUN yarn app:build

FROM node:16-alpine as deps
WORKDIR /app
COPY package.json yarn.lock ./
RUN yarn install --production --frozen-lockfile

FROM node:16-alpine
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY --from=dist /app/package.json /app/.env ./
COPY --from=dist /app/dist/src ./src

EXPOSE 3090
# CMD du -sh ./node_modules/* | sort -nr | grep '\dM.*'
CMD node src/app.js
```

In line 19 I comment a sh command to print size of depencencies in `node_modules`. So you can check what dependencies remained in the final build and possibly remove some of them, or replace them with the optimal version. For example, if you use AWS S3 in your application, you can use a dependency only for S3 and not for all AWS services.

Final size of the Docker Image is 322Mb, which 4x times smaller than original image.

```sh
> docker images | grep app
app     latest    b6f283f00bb2   12 seconds ago   322MB
```

## Conclusion

Using simple things you can reduce the size of the image of your application and speed up the time between building and running the application in the production.

---

That’s all for now. I hope that article was useful for you. If yes, don’t forget to follow me to get new updates.
