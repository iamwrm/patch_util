#!/bin/bash
set -e  # Exit on error


export BUILD_LOG_LEVEL=DEBUG

uv pip install ./python_wrapper --force-reinstall -v

if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

my_c_app --test

file $(which my_c_app)
