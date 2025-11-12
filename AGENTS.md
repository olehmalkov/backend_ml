Objective: Your task is to develop a Python-based service that leverages a pre-provided
FeatureDetector class for computationally intensive image feature detection.
This service will expose a REST API for image processing, manage requests and responses
with a database, and ensure efficient operation via Docker.
Background:
You are provided with a FeatureDetector class that performs image loading and feature
detection. This class is designed to be part of an asynchronous service, including a warm-up
phase for any necessary preparatory tasks. Your role is to integrate this class into a fully
functional service, following the requirements below.
Infrastructure
1. The service should be built of two units:
a. A REST API module that receives requests
b. A database for saving and caching responses - you may choose your
database
2. Use any tools and infrastructure that you wish to make the service easy to deploy.
We recommend using docker compose
Requirements:
1. Containerization:
○ Containerize the Python service using Docker, ensuring all dependencies are
included for the application to run.
2. Database Logging:
○ Integrate a database (of your choice) in a separate container. Log all API
requests and processing results.
○ Implement logic to check if an image has been processed previously. If so,
return the saved response instead of reprocessing the image.
3. Integration of the FeatureDetector Class:
○ Use the provided FeatureDetector class without modification. This class
uses the OpenCV library for SIFT feature detection and includes a warm-up
phase.
4. REST API:
○ Develop a REST API with the following endpoints:
■ /process-image: Accepts an image file, processes it using the
FeatureDetector class, and returns the feature detection results.
■ /check-status: Returns the service's readiness status, indicating
whether the FeatureDetector class has completed its warmup
phase.
○ Ensure the API is asynchronous to efficiently handle concurrent requests.
Deliverables:
● Source code for the service, including all necessary dependencies and environment
setup instructions, incorporating the provided FeatureDetector class.
● Dockerfile for the Python service.
● Any script or configuration required to build and run the service and the database on
a local machine.
● Readme file with documentation on how to deploy and send a request to the service.
Evaluation Criteria:
● Functionality: The service should correctly integrate the FeatureDetector class
to process images and return expected results.
● Code Quality: Your code should be well-structured, clearly documented, and follow
best practices.
● Database Integration: The service efficiently uses the database for logging and
optimizing processing by preventing duplicate work