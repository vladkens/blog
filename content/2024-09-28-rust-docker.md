---
title: Fast multi-arch Docker build for Rust projects
slug: fast-multi-arch-docker-for-rust
date: 2024-10-04
taxonomies:
  tags: ["rust", "docker"]
---

## Rust vs other languages

Rust allows programs to run very fast and memory efficient, but it has a cost – compile time. In web development, it is standard practice to deliver programs as Docker images and then run them in Kubernetes / [Amazon ECS](/aws-ecs-cluster) / Docker Compose / etc. After the popularity of ARM processors in recent years, programmers have been faced with the additional step of preparing multi-arch Docker images (meaning that the same image should be able to run natively on both x86-64/amd64 and aarch64/arm64 processors).

Preparing Docker images for interpreted languages is usually not a problem – Docker Buildx is used, which in turn runs inside the emulator and builds the image for each architucture natively. NodeJS / Python just install dependencies via npm / pip, copy the project code, does a little polishing and that's pretty much it. Even in compiled Go this approach works fine because Go has an extensive standard library. In the case of Rust, compiling even a simple web application is a rebuilding of the “universe” – almost any web application requires: HTTP-server, HTTP-client (which in turn requires a library to work with cryptography for https), asynchronous runtime (tokie, etc), serialization/desirialization (serde, serde_json); which in Rust should be installed as external libraries (crates) and should be compiled each time when program builded.

Although Rust compiler has a lot of work to do, it can do it quickly. Even not strongest CI, will build an average project in a couple of minutes. However, this is true only in case of building on native architecture (for example building amd64 binary on an amd64 processor). As soon as we need to build a multi-arch image, we have to do emulation and the compilation speed drops dramatically. For example, on my simple public project – [ghstats](https://github.com/vladkens/ghstats), building multi-arch image from scratch took about 50 minutes, when same build for native architecture takes 2-3 minutes.

Building time can be optimized by proper usage of Docker layers, so that the step with rebuilding dependencies occurs only when they are actually changed. So only the first build will be long and following builds will be fast. Unfortunately, Rust infrastructure have a problem in this point –
any change in `Cargo.toml` file (for example version number) will invalidate Docker layer and triggers full rebuild of all dependencies.

## Problem definition

So there are two problems with building multi-arch Docker images for Rust projects:

1. Layer invalidation and full rebuild on any change in `Cargo.toml `
2. Very slow multi-arch build due to emulation

## Better dependencies building

Easiest way to solve the first problem is to use `cargo-chef` which was created exacly for it. `cargo-chef` converts `Cargo.toml` & `Cargo.lock` into a special `recipe.json` file that will remain unchanged until project dependencies are unchanged. Then we can use this json file to cache expensive Docker layer that compiles dependencies.

Dockerfile with `cargo-chef` will use multi-stage build splited to 5 parts:

1. Installing `cargo-chef` and build dependencies (OpenSSL, linux-headers, etc)
2. Preparing `recipe.json` file with project dependencies description
3. Installing & builiding project dependencies from `recipe.json`
4. Building whole project
5. Copy binaries to runtime image and final polishing

Example of Dockerfile with `cargo-chef` and multi-stage build (I use alpine in my projects, but you can use other base-images).

```dockerfile
# (1) installing cargo-chef & build deps
FROM rust:alpine AS chef
WORKDIR /app
RUN cargo install --locked cargo-chef
RUN apk add --no-cache musl-dev openssl-dev

# (2) prepating recipe file
FROM chef AS planner
COPY . .
RUN cargo chef prepare --recipe-path recipe.json

# (3) building project deps, cache magic happen on COPY command
FROM chef AS builder
COPY --from=planner /app/recipe.json recipe.json
RUN cargo chef cook --recipe-path recipe.json --release

# (4) actual project build
COPY . .
RUN cargo build -r

# (5) runtime image, you can use any base image you want
FROM alpine:latest AS runtime
WORKDIR /app
COPY --from=builder /app/target/release/prog /app/prog
CMD "/app/prog"
```

This approach will speed up Docker image build many times while project dependencies are not changed. Because Docker builds stages separately, _planner_ stage will be executed each time (but `cargo-chef` is fast!) and _builder_ stage will be partially cached until `recipe.json` file are same.

If you need single architecture build this will work fine. But if you need multi-arch images, this approach still be slow.

## Multi-arch image with cross-compilation

Multi-arch builds using Docker Buildx run very slow due to QEMU emulation. If we get rid of emulation, compilation will be at full speed. Rust has built-in cross-compilation for other architectures, so we adapt it in Docker build.

Cross-compilation in Rust itself works fine, but some crates are based on C libraries (OpenSSL, SQLite, etc). Compiling and linking C code is quite complicated and not always clear (usually you have to look for error codes somewhere on Stack Overflow or Github Issues until you get the right set of compilers/header files added). There is another tool that surprisingly solves the problem of cross-compiling C code very well – Zig (actually this is programming language, but they have build toolchain as well).

To connect Zig build toolchain with Rust I will use `cargo-zigbuild` crate. I other Docker file looks pretty same to our `cargo-chef` variant, expect I added second target in Cargo to build and `cargo build` replaced with `cargo zigbuild`.

```dockerfile
# (1) this stage will be run always on current arch
# zigbuild & Cargo targets added
FROM --platform=$BUILDPLATFORM rust:alpine AS chef
WORKDIR /app
ENV PKG_CONFIG_SYSROOT_DIR=/
RUN apk add --no-cache musl-dev openssl-dev zig
RUN cargo install --locked cargo-zigbuild cargo-chef
RUN rustup target add x86_64-unknown-linux-musl aarch64-unknown-linux-musl

# (2) nothing changed
FROM chef AS planner
COPY . .
RUN cargo chef prepare --recipe-path recipe.json

# (3) building project deps: need to specify all targets; zigbuild used
FROM chef AS builder
COPY --from=planner /app/recipe.json recipe.json
RUN cargo chef cook --recipe-path recipe.json --release --zigbuild \
  --target x86_64-unknown-linux-musl --target aarch64-unknown-linux-musl

# (4) actuall project build for all targets
# binary renamed to easier copy in runtime stage
COPY . .
RUN cargo zigbuild -r
    --target x86_64-unknown-linux-musl --target aarch64-unknown-linux-musl && \
  mkdir /app/linux && \
  cp target/aarch64-unknown-linux-musl/release/prog /app/linux/arm64 && \
  cp target/x86_64-unknown-linux-musl/release/prog /app/linux/amd64

# (5) this staged will be emulated as was before
# TARGETPLATFORM usage to copy right binary from builder stage
# ARG populated by docker itself
FROM alpine:latest AS runtime
WORKDIR /app
ARG TARGETPLATFORM
COPY --from=builder /app/${TARGETPLATFORM} /app/prog
CMD "/app/prog"
```

In general that all. Such build approach will work faster. For my project:

1. initial build 50 min -> 13 min (3.8x)
2. code updated 7 min -> 3 min (2.3x)

Additional performance can be achieved by moving first step into separate base image, then our main Docker image will not need to build `cargo-zibguild` and `cargo-chef` (-2 min from initial build).

---

Sources:

1. <https://www.docker.com/blog/faster-multi-platform-builds-dockerfile-cross-compilation-guide>
