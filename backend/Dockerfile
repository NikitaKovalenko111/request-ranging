FROM golang:1.25-alpine AS builder

WORKDIR /src
COPY go.mod ./
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -trimpath -ldflags="-s -w" -o /out/executor-balancer ./cmd/balancer

FROM alpine:3.22

RUN addgroup -S app && adduser -S -G app app
USER app
COPY --from=builder /out/executor-balancer /usr/local/bin/executor-balancer
EXPOSE 8090
ENTRYPOINT ["executor-balancer"]
