#!/usr/bin/env bash

set -ex

source devops/docker_build/entrypoint/patch_environment_variables.sh
source devops/docker_build/entrypoint/gh_action_aws_credentials.sh

mount -a || true

source ~/.bashrc
conda activate venv

# Allow working with files outside a container.
umask 000

./devops/docker_build/test/test_mount_fsx.sh
./devops/docker_build/test/test_mount_s3.sh

exec "$@"
