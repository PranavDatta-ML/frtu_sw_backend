#!/bin/bash

# Read the version from the version.txt file
VERSION=$(cat version.txt)

# Build the Docker image and tag it with the version
docker build --build-arg VERSION=$VERSION -t web-app:$VERSION .
docker build --build-arg VERSION=$VERSION -t web-app:latest .