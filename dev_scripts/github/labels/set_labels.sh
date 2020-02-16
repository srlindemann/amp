#!/bin/bash -e

# """
# Backup and then update labels of several GitHub repos.
# """

EXEC="/Users/saggese/src/github/github-label-maker/github-label-maker.py"

SRC_DIR="./dev_scripts/github/labels"
DST_DIR="$SRC_DIR/backup"


function label() {
    FULL_OPTS="$OPTS -o $OWNER -r $REPO"
    CMD="python $EXEC $FULL_OPTS -t $GH_TOKEN"
    echo "> $CMD"
    eval $CMD
    echo "Done"
}


# ParticleDev/commodity_research
OWNER="ParticleDev"
REPO="commodity_research"
if [[ 1 == 1 ]]; then
    # Backup.
    FILE_NAME="$DST_DIR/labels.$OWNER.$REPO.json"
    OPTS="-d $FILE_NAME"
    label

    # Update.
    FILE_NAME="$SRC_DIR/gh_tech_labels.json"
    OPTS="-m $FILE_NAME"
    label
fi;

# ParticleDev/infra
OWNER="ParticleDev"
REPO="infra"
if [[ 1 == 1 ]]; then
    # Backup.
    FILE_NAME="$DST_DIR/labels.$OWNER.$REPO.json"
    OPTS="-d $FILE_NAME"
    label

    # Update.
    FILE_NAME="$SRC_DIR/gh_tech_labels.json"
    OPTS="-m $FILE_NAME"
    label
fi;

# alphamatic/amp
OWNER="alphamatic"
REPO="amp"
if [[ 1 == 1 ]]; then
    # Backup.
    FILE_NAME="$DST_DIR/labels.$OWNER.$REPO.json"
    OPTS="-d $FILE_NAME"
    label

    # Update.
    FILE_NAME="$SRC_DIR/gh_tech_labels.json"
    OPTS="-m $FILE_NAME"
    label
fi;
