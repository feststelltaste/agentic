# JDK + Maven + Gradle, unprivileged. Multiple JDKs: each commit may need a different one (state the toolchain deviation in the report).
FROM eclipse-temurin:21-jdk
RUN apt-get update && apt-get install -y --no-install-recommends git maven curl unzip ca-certificates fonts-dejavu-core \
 && rm -rf /var/lib/apt/lists/*
# Optionally more JDKs: e.g. COPY --from=eclipse-temurin:17-jdk /opt/java/openjdk /opt/jdk17 ; then set JAVA_HOME per run.
RUN useradd -m -u 1000 -s /bin/bash vscode && mkdir -p /cache && chown vscode /cache
USER vscode
# Important: Java builds need network (Maven Central, Gradle distribution) and run plugins/build scripts.
# No credentials in the container, no ~/.m2/settings.xml from the host, no tokens in environment variables.
