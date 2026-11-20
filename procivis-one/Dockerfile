# Local educational build from the commit checked by scripts/prepare.py.
FROM rust:1.95.0-bookworm@sha256:6258907abe69656e41cd992e0b705cdcfabcbbe3db374f92ed2d47121282d4a1 AS build
RUN apt-get update && apt-get install -y --no-install-recommends cmake clang libclang-dev && rm -rf /var/lib/apt/lists/*
WORKDIR /src
COPY . .
ENV CARGO_BUILD_JOBS=4 CARGO_PROFILE_DEV_DEBUG=0 APP_VERSION=v1.87.2
RUN --mount=type=cache,target=/usr/local/cargo/registry --mount=type=cache,target=/src/target \
    cargo build --locked -p core-server && cp target/debug/core-server /core-server
FROM debian:bookworm-slim@sha256:7c7b2c966bc9ee8cedfeef67e0e279108992c77681fa595db4a9d65c06ccc587
WORKDIR /app
COPY --from=build /core-server /app/core-server
COPY --from=build /src/config /app/config
COPY --from=build /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt
USER 1000:1000
EXPOSE 18104
ENTRYPOINT ["/app/core-server"]
CMD ["--config", "config/config-procivis-base.yml", "--config", "/lab/override.json"]
