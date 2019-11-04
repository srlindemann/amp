#!/bin/bash -xe

# """
# - Build conda env
# - Run the fast tests with coverage
# """

EXEC_NAME=`basename "$0"`
AMP="."
CONDA_ENV="amp_develop.build_clean_env.run_fast_coverage_tests"
VERB="DEBUG"
CREATE_CONDA_PY="./dev_scripts/install/create_conda.py"

# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
# Init.
# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

echo "$EXEC_NAME: source ~/.bashrc"
source ~/.bashrc
# TODO(gp): This used to be needed.
#export PYTHONPATH=""

echo "$EXEC_NAME: source $AMP/dev_scripts/helpers.sh"
source $AMP/dev_scripts/helpers.sh

# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
# Build env.
# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

# Activate conda base environment.
echo "$EXEC_NAME: conda activate base"
conda activate base

# Configure base environment.
echo "$EXEC_NAME: source $AMP/dev_scripts/setenv.sh -e base"
source $AMP/dev_scripts/setenv.sh -e base

# Print env.
echo "$EXEC_NAME: env"
env

# From dev_scripts/create_conda.sh
CMD="$CREATE_CONDA_PY --env_name $CONDA_ENV --req_file dev_scripts/install/requirements/develop.yaml --delete_env_if_exists -v $VERB"
frame "$EXEC_NAME: $CMD"
execute $CMD

# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
# Setenv.
# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

# Config environment.
echo "$EXEC_NAME: source dev_scripts/setenv.sh -e $CONDA_ENV"
source dev_scripts/setenv.sh -e $CONDA_ENV

# Check conda env.
CMD="print_conda_packages.py"
frame "$EXEC_NAME: $CMD"
execute $CMD

CMD="check_develop_packages.py"
frame "$EXEC_NAME: $CMD"
execute $CMD

# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
# Run.
# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

# Run tests.
OPTS='--test fast --coverage'
CMD="dev_scripts/run_tests.py $OPTS --jenkins -v $VERB"
frame "$EXEC_NAME: $CMD"
execute $CMD
