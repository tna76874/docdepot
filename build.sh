#!/bin/bash

# Usage: ./build.sh [DOCKERFILE] [IMAGEAPPEND]

# Setze Variablen
DOCKERFILE=${1:-Dockerfile}
IMAGEAPPEND=${2:-}

# Setze Variablen, falls sie nicht bereits gesetzt sind (nützlich für lokale Ausführung)
: "${GITHUB_REF:=refs/heads/$(git symbolic-ref --short HEAD)}"
: "${GITHUB_REPOSITORY:=$(git config --get remote.origin.url | sed 's/.*github.com.//;s/.git$//')}"

COMMIT_HASH=$(git rev-parse HEAD)
CURRENT_DATE=$(date +'%Y%m%d')
CURRENT_DATE_WITH_HOUR=$(date +'%Y%m%d%H')
IMAGE_NAME="ghcr.io/${GITHUB_REPOSITORY}${IMAGEAPPEND}"

# Festlegen des Kanals basierend auf dem Branch
CHANNEL=""
if [ "$GITHUB_REF" == "refs/heads/master" ] || [ "$GITHUB_REF" == "refs/heads/main" ]; then
  CHANNEL="latest"
elif [ "$GITHUB_REF" == "refs/heads/stable" ]; then
  CHANNEL="stable"
fi
echo "CHANNEL ${CHANNEL}"
echo "IMAGE_NAME ${IMAGE_NAME}"

# Funktion zum Bauen des Docker-Images
build_image() {
  TAG=$1
  docker build . --file ${DOCKERFILE} --tag ${IMAGE_NAME}:${TAG}
}

# Funktion zum Pushen des Docker-Images
push_image() {
  TAG=$1
  docker push ${IMAGE_NAME}:${TAG}
}

# Build für den stable-Branch
if [ "$CHANNEL" == "stable" ]; then
  build_image "${CHANNEL}-${CURRENT_DATE}"
  build_image "${CHANNEL}-${CURRENT_DATE_WITH_HOUR}"
fi

# Build für den Commit-Hash
build_image "${COMMIT_HASH}"

# Build für den Kanal (falls gesetzt)
if [ -n "$CHANNEL" ]; then
  build_image "${CHANNEL}"
fi

# Push-Operationen nur durchführen, wenn im CI-Umgebung (GitHub Actions)
if [ "$CI" == "true" ]; then
  if [ "$CHANNEL" == "stable" ]; then
    push_image "${CHANNEL}-${CURRENT_DATE}"
    push_image "${CHANNEL}-${CURRENT_DATE_WITH_HOUR}"
  fi

  push_image "${COMMIT_HASH}"

  if [ -n "$CHANNEL" ]; then
    push_image "${CHANNEL}"
  fi
else
  echo "Lokale Ausführung erkannt - Docker-Images werden nicht gepusht."
fi
