# Makefile providing common development tasks for the feature detection service

# Default image name. Override on the command line if necessary, e.g.:
# make build IMAGE=myuser/feature-detector:latest
IMAGE ?= feature-detector

.PHONY: test build run

# Run the Python test suite
test:
	pytest -q

# Build the Docker image for the API service
build:
	docker build -t $(IMAGE) .

# Launch the full stack using docker compose
run:
	docker compose up --build