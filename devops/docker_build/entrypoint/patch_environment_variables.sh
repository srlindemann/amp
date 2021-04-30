#!/usr/bin/env bash

# TODO(gp): We should merge it with `source dev_scripts/setenv_amp.sh`.

set -e

# Print the name of this file.
FILE_NAME="docker_build/entrypoint/patch_environment_variables.sh"
echo "##> $FILE_NAME"

PWD=$(pwd)
AMP=$PWD

# #############################################################################
# PATH
# #############################################################################

echo "# Set PATH"

export PATH=.:$PATH

export PATH=$AMP:$PATH
export PATH=$AMP/dev_scripts:$PATH
export PATH=$AMP/dev_scripts/aws:$PATH
export PATH=$AMP/dev_scripts/git:$PATH
export PATH=$AMP/dev_scripts/infra:$PATH
export PATH=$AMP/dev_scripts/install:$PATH
export PATH=$AMP/dev_scripts/notebooks:$PATH
export PATH=$AMP/dev_scripts/testing:$PATH
export PATH=$AMP/documentation/scripts:$PATH

export PATH=$(echo $PATH | perl -e 'print join(":", grep { not $seen{$_}++ } split(/:/, scalar <>))')
echo "PATH=$PATH"

#echo $PATH | perl -e 'print join("\n", grep { not $seen{$_}++ } split(/:/, scalar <>))'

# #############################################################################
# PYTHONPATH
# #############################################################################

echo "# Set PYTHONPATH"
export PYTHONPATH=$PWD:$PYTHONPATH

export PYTHONPATH=$(echo $PYTHONPATH | perl -e 'print join(":", grep { not $seen{$_}++ } split(/:/, scalar <>))')

echo "PYTHONPATH=$PYTHONPATH"

#echo $PYTHONPATH | perl -e 'print join("\n", grep { not $seen{$_}++ } split(/:/, scalar <>))'

# #############################################################################
# Configure environment
# #############################################################################

echo "# Configure env"
export PYTHONDONTWRITEBYTECODE=x
