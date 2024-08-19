---
title: How to see env in Docker container?
slug: docker-container-env
date: 2022-12-06
taxonomies:
  tags: ["docker", "tricks"]
---

## TL;DR

```sh
# get all
cat /proc/1/environ | tr '\0' '\n'

# get by name
cat /proc/1/environ | tr '\0' '\n' | grep ABC
```

## Details

When you develop services, sometimes you need to know what environment variables a process in a container is running with.

For example if you use kubernetes and the environment variables come from several places or if you debug a production container and want to know what environment it is running with.

Well, that's easy. Normally your process in the docker is running under `PID=1`. You can check this by running the command:

```sh
docker exec <CONTAINER_ID> ps aux
# output:
PID   USER     TIME  COMMAND
    1 root      0:02 node src/main.js
```

Now we can see the environment variables that this process uses:

```sh
docker exec <CONTAINER_ID> cat /proc/1/environ | tr '\0' '\n'
# output:
NODE_VERSION=16.18.1
HOSTNAME=544193567d05
YARN_VERSION=1.22.19
SHLVL=2
HOME=/root
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
PWD=/app
```

This approach is also useful if you need to get environment variables of kubernetes pod:

```sh
# connect to pod
kubectl exec --stdin --tty node-app-abc123 -- /bin/sh

# get process envs
cat /proc/1/environ | tr '\0' '\n'
# output: list of environment variables
```