---
title: Docker Compose templating using YAML merge feature
slug: docker-compose-merge
date: 2022-12-13
taxonomies:
  tags: ["docker"]
---

Useful trick when you have many of the same services in the `docker-compose.yml` file.

Imagine that we have some data processing application which has a master service and several different workers. All applications are written in the same language and use a common base docker container. In general this is a fairly common configuration. The `docker-compose.yml` file will look something like this:

```yaml
version: "3.8"

services:
  master:
    build:
      context: .
    ports:
      - "8080:8080"
    volumes:
      - ".:/app"
    command: python run_master.py

  worker-foo:
    build:
      context: .
    depends_on:
      - master
    volumes:
      - ".:/app"
    environment:
      - MASTER_HOST=master:8080
    command: python run_foo_worker.py

  worker-bar:
    build:
      context: .
    depends_on:
      - master
    volumes:
      - ".:/app"
    environment:
      - MASTER_HOST=master:8080
    command: python run_bar_worker.py
```

It looks verbose. A lot of code duplication. Let’s fix it with YAML Anchors!

```yaml
version: "3.8"

x-base: &base
  build:
    context: .
  volumes:
    - .:/app

x-worker: &worker
  <<: *base
  depends_on:
    - master
  environment:
    - MASTER_HOST=master:8080

services:
  master:
    <<: *base
    ports:
      - "8080:8080"
    command: python run_master.py

  worker-foo:
    <<: *worker
    command: python run_foo_worker.py

  worker-bar:
    <<: *worker
    command: python run_bar_worker.py
```

It looks much better! Such a file is easier to maintain, expand and edit in the future.

The x-field is a special property in the docker-compose.yml file. In the Docker compose documentation they are called [extension fields](https://docs.docker.com/compose/compose-file/#extension). You can put any valid YAML code in them.

## Merge problems

Note that YAML does merge at the top level and do not deep merge. So this code will not work as expected:

```yaml
x-base: &base
  environment:
    - SUPER_SECRET=42

x-worker: &worker
  <<: *base
  environment:
    - MASTER_HOST=master:8080
```

The `worker` service will completely overwrite environment of base and will contain only `MASTER_HOST`. Unfortunately, this array combining cannot be achieved directly in the docker-compose file. Therefore, in such cases, you can use [extends](https://docs.docker.com/compose/multiple-compose-files/extends/).

## Solution for single variable

However, if you want to make only one value common, you can put that value into a variable, and use that variable as an array element.

```yaml
x-super-secret: &super-secret SUPER_SECRET=42

x-base: &base
  environment:
    - *super-secret

x-worker: &worker
  <<: *base
  environment:
    - *super-secret
    - MASTER_HOST=master:8080
```

This can be useful for `volumes`, `depends_on` and other array-like directives.

## Solution for single object

As for environment, you can put the shared variables in a separate object and combine them in the same way we did with services. 🙃

```yaml
x-env: &env
  SUPER_SECRET: 42

x-base: &base
  environment:
    <<: *env

x-worker: &worker
  <<: *base
  environment:
    <<: *env
    MASTER_HOST: master:8080
```

---

That’s all for now. If this information was helpful to you, don’t forget to subscribe to receive notifications of new posts.
