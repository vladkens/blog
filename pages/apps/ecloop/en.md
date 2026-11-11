---
title: ecloop
order: 11
tagline: CPU tool for computing public keys on the secp256k1 elliptic curve.
blurb: A C program for fast secp256k1 math and hash160 search on the CPU. I built it to learn elliptic curves and low-level optimization.
language: C
repos:
  GitHub: https://github.com/vladkens/ecloop
links:
  bitcointalk thread: https://bitcointalk.org/index.php?topic=5544649.0
posts:
  - rmd160-simd
---

ecloop computes public keys on the secp256k1 elliptic curve and searches their hash160 values, compressed and uncompressed. It's written in C and tuned for the CPU: fixed 256-bit modular arithmetic, group inversion for point addition, precomputed tables for multiplication, SHA-256 with the SHA extension on ARM and x86, and RIPEMD-160 with SIMD on AVX2 and NEON. It works on macOS and Linux, and on Windows through WSL.

It's for people interested in how this math gets fast, and for those who like Bitcoin Puzzles. I built it to explore the mathematics behind elliptic curves and to practice low-level programming. Searching for puzzles was added as a real-world use case. The chances of finding a private key from a used address tend toward zero, so brute force on them is pointless. For me it's a collection of tricks, and I wrote about one of them in [Optimizing RIPEMD-160 with SIMD](/rmd160-simd/).

## Build

```sh
git clone https://github.com/vladkens/ecloop.git && cd ecloop
make build
```

On macOS you may need to run `xcode-select --install` first. Some compiler versions have issues with the built-ins used in the code, so check the build:

```sh
make add
make mul
```

`make add` should find 9 keys and `make mul` should find 1080. To see the speed of the internal functions on your machine:

```sh
./ecloop bench
```
