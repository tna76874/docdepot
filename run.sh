#!/bin/bash
IMAGE="ghcr.io/tna76874/docdepot:edge"
docker build -t ${IMAGE} .
docker run -p 5000:5000 --name docdeposer-container --rm -v $(pwd)/data:/app/data ${IMAGE}
