# Feature Detection Service

This service provides a REST API for feature detection in images. It uses a `FeatureDetector` class to perform SIFT feature detection and caches the results in a MongoDB database.

## Prerequisites

- Docker
- Docker Compose

## Local development

1. **Set up your environment variables**

   Create a `.env` file by copying the `.env.example` file and update it with your MongoDB credentials:

   ```bash
   cp .env.example .env
   ```

 
2. **Build and run the services using Docker Compose**

   ```bash
   docker compose up --build
   ```

   The API will be available at `http://localhost:5000` and MongoDB at `mongodb://localhost:27017`.

3. **Stop the stack**

   ```bash
   docker compose down
   ```

   Add the `-v` flag if you also want to remove MongoDB volumes when tearing the stack down.

## Development workflow

This repository follows several MLOps best practices to make the service easy to develop and deploy.

- **Reproducible builds:** Dependencies are declared in `requirements.txt`, and containerization is used to ensure the same environment across machines.
- **Continuous integration:** GitHub Actions runs static analysis and unit tests on every push to verify that the code compiles and behaves as expected.
- **Testing:** A small test suite lives in the `tests/` directory. You can run it locally with `make test` or `pytest`.
- **Code formatting:** A `.pre-commit-config.yaml` is provided with [black](https://github.com/psf/black) and [flake8](https://flake8.pycqa.org/) hooks. Installing pre‑commit (`pip install pre-commit`) and running `pre-commit install` will automatically format and lint your code on each commit.

### Running tests

To run the Python unit tests locally, execute:

```bash
make test
```

This will invoke `pytest` and report any failures. These tests are also executed automatically in the CI pipeline.

### Building and running the service

You can build the Docker image and start the service via Docker Compose using the provided `Makefile`:

```bash
# Build the API image
make build IMAGE=myuser/feature-detector:latest

# Run the full stack (API + MongoDB)
make run
```

Environment variables such as `MONGO_URL` must be set in your environment or passed via Docker Compose.

## Continuous integration and delivery

GitHub Actions (see `.github/workflows/ci.yml`) validates every change on pull requests and builds a production image on pushes to the `main` branch. The workflow keeps credentials outside of the repository by reading them from repository secrets.

### Required GitHub secrets

| Secret | Purpose |
| ------ | ------- |
| `DOCKERHUB_USERNAME` | Docker Hub account used to publish container images. |
| `DOCKERHUB_TOKEN` | Access token (or password) for the Docker Hub account. |

Optionally set `MONGO_INITDB_ROOT_USERNAME`, `MONGO_INITDB_ROOT_PASSWORD`, and `MONGO_URL` as repository or environment secrets if you run integration tests that need database access. These values should mirror the ones used in your local `.env` file but must never be stored in Git history.

The Docker image published by the workflow is tagged using metadata derived from the Git ref (for example, `latest` on `main` and semantic tags on releases) and is pushed to `docker.io/<DOCKERHUB_USERNAME>/<repository-name>`.

## API Endpoints

### `/check-status`

- **Method:** `GET`
- **Description:** Checks the readiness of the service. The service is ready when the `FeatureDetector` class has completed its warmup phase.
- **Responses:**
  - `200 OK`: `{"status": "ready"}`
  - `503 Service Unavailable`: `{"status": "warming up"}`

### `/process-image`

- **Method:** `POST`
- **Description:** Processes an image to detect features. The image should be sent as a multipart form data with the key `image`.
- **Example Request:**

  ```bash
  curl -X POST -F "image=@/path/to/your/image.jpg" http://localhost:5000/process-image
  ```

- **Responses:**
  - `200 OK`: A JSON object with the feature detection results.
  - `400 Bad Request`: If no image file is provided.
  - `503 Service Unavailable`: If the service is not ready.
  - `500 Internal Server Error`: If an error occurs during processing.

Quick Demo Script

# 1. Check service status
Write-Host "`n=== 1. Service Status ===" -ForegroundColor Green
curl.exe http://localhost:5000/check-status

# 2. First image processing (no cache)
Write-Host "`n=== 2. First Request (No Cache) ===" -ForegroundColor Yellow
Measure-Command { curl.exe -X POST -F "image=@test.jpg" http://localhost:5000/process-image }

# 3. Same image (with cache)
Write-Host "`n=== 3. Second Request (With Cache) ===" -ForegroundColor Cyan
Measure-Command { curl.exe -X POST -F "image=@test.jpg" http://localhost:5000/process-image }

# 4. Different image (no cache)
Write-Host "`n=== 4. Different Image (No Cache) ===" -ForegroundColor Yellow
Measure-Command { curl.exe -X POST -F "image=@flower.jpg" http://localhost:5000/process-image }

# 5. Same different image (with cache)
Write-Host "`n=== 5. Same Image Again (With Cache) ===" -ForegroundColor Cyan
Measure-Command { curl.exe -X POST -F "image=@flower.jpg" http://localhost:5000/process-image }

Write-Host "`n=== Demo Complete! ===" -ForegroundColor Green

 Cleanup After Demo

 # Stop services
docker-compose down

# Remove volumes (optional)
docker-compose down -v