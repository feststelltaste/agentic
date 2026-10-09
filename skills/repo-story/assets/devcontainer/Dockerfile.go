FROM golang:1
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates && rm -rf /var/lib/apt/lists/*
RUN useradd -m -u 1000 -s /bin/bash vscode && mkdir -p /cache && chown vscode /cache
USER vscode
# Go needs network for modules. Old go.mod files may ask for another toolchain (go line): state the deviation in the report.
