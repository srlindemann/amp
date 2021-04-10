#!/bin/bash -e

python -m venv venv
source venv/bin/activate
pip install -r dev_scripts/client_setup/requirements.txt

aws --version

echo "# Activate with:"
echo "source venv/bin/activate"
