#!/usr/bin/env bash

curl https://${HOST}/v1/completions \
    -H "Content-Type: application/json" \
    -d '{
        "model": "'${MODEL_NAME}'",
        "prompt": "San Francisco is a",
        "max_tokens": 1000,
        "temperature": 0
    }' \
-u "${USER}:${PASSWORD}"
