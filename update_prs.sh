#!/bin/bash

# Get the list of tags in commit order
TAGS=$(git tag --merged)

# Convert tags into an array
TAG_ARRAY=($TAGS)

# Number of tags
NUM_TAGS=${#TAG_ARRAY[@]}

# Check if there are enough tags
if [ $NUM_TAGS -lt 1 ]; then
    echo "No tags found in the repository."
    exit 1
fi

# Iterate over the tags and create PRs
for (( i=0; i<$NUM_TAGS; i++ ))
do
    branch=${TAG_ARRAY[$i]}
    echo "Updating branch $branch..."
    # set -x
    git push --force-with-lease origin HEAD:refs/heads/"${branch}"
    # url=$(git push --force-with-lease origin HEAD:refs/heads/"${branch}" 2>&1 | grep -Eo "https://.*" | head -n 1)
    # open ${url}
done

echo "Remote branches updated!"
