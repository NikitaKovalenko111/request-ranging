.PHONY: run test fmt vet build

run:
	go run ./cmd/balancer

test:
	go test ./...

fmt:
	gofmt -w ./cmd ./internal

vet:
	go vet ./...

build:
	go build -o bin/executor-balancer ./cmd/balancer
