# syntax=docker/dockerfile:1

FROM maven:3.9-eclipse-temurin-17 AS builder
WORKDIR /build

# 先拷贝 pom.xml 利用层缓存下载依赖
COPY backend/pom.xml backend/pom.xml
COPY simulator/pom.xml simulator/pom.xml
RUN mvn -f backend/pom.xml -B dependency:go-offline \
 && mvn -f simulator/pom.xml -B dependency:go-offline

# 拷贝源码并编译打包（包含最新 demo-f2 演示数据集与 V1~V33 迁移脚本）
COPY backend/src backend/src
COPY simulator/src simulator/src
COPY scripts/PasswordHash.java scripts/PasswordHash.java

RUN mvn -f backend/pom.xml -B clean package -DskipTests \
 && mvn -f simulator/pom.xml -B clean package -DskipTests \
 && mkdir -p /app/bootstrap \
 && mvn -f backend/pom.xml -q dependency:build-classpath -Dmdep.outputFile=/tmp/cp.txt \
 && javac -cp "$(cat /tmp/cp.txt)" -d /app/bootstrap scripts/PasswordHash.java \
 && (cd /app/bootstrap && jar xf /build/backend/target/airport-ai-app-1.0.0.jar BOOT-INF/lib \
     && find BOOT-INF/lib \( -name 'spring-security-crypto-*.jar' -o -name 'spring-jcl-*.jar' \) -exec mv {} /app/bootstrap/ \; \
     && rm -rf BOOT-INF)

FROM eclipse-temurin:17-jre-jammy
WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/* \
 && groupadd -r airportai \
 && useradd -r -g airportai -d /app -s /usr/sbin/nologin airportai

COPY --from=builder /build/backend/target/airport-ai-app-1.0.0.jar /app/airport-ai-app.jar
COPY --from=builder /build/simulator/target/device-simulator-runtime.jar /app/device-simulator-runtime.jar
COPY --from=builder /app/bootstrap /app/bootstrap

RUN chown -R airportai:airportai /app

USER airportai
EXPOSE 8080

HEALTHCHECK --interval=10s --timeout=5s --retries=12 --start-period=30s \
  CMD curl -fsS http://127.0.0.1:8080/actuator/health | grep -q '"status":"UP"' || exit 1

ENTRYPOINT ["java", "-Xms512m", "-Xmx2g", "-jar", "/app/airport-ai-app.jar"]
