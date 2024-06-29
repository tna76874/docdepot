#!/bin/bash
if ! git diff-index --quiet HEAD --; then
    echo "Es gibt uncomittete Änderungen im Repository. Bitte committen Sie Ihre Änderungen zuerst."
    exit 1
fi

base_items=(
            "requirements.txt"
            "Dockerfile_base"
            )
change_found=false

for item in "${base_items[@]}"
do
    if ! git diff --quiet HEAD^ -- "$item"; then
        change_found=true
        break
    fi
done

if [ "$change_found" = true ]; then
    ./build.sh Dockerfile_base base
fi

./build.sh Dockerfile