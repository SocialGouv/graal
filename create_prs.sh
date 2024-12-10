#!/bin/bash

# Base branch for the first PR
BASE_BRANCH="main"

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

# Push all tags to the remote
echo "Pushing tags to remote..."
git push --tags

# Iterate over the tags and create PRs
for (( i=0; i<$NUM_TAGS; i++ ))
do
  if [ $i -eq 0 ]; then
    # First PR: from base branch to the first tag
    HEAD=${TAG_ARRAY[$i]}
    echo "Creating PR from $BASE_BRANCH to $HEAD..."
    git push origin "$HEAD:refs/heads/$HEAD" # Push the tag as a branch
    gh pr create --base "$BASE_BRANCH" --head "$HEAD" --title "PR: $BASE_BRANCH to $HEAD" --body "Changes between $BASE_BRANCH and $HEAD."
  else
    # Subsequent PRs: from tag[i-1] to tag[i]
    BASE=${TAG_ARRAY[$i-1]}
    HEAD=${TAG_ARRAY[$i]}
    echo "Creating PR from $BASE to $HEAD..."
    git push origin "$HEAD:refs/heads/$HEAD" # Push the tag as a branch
    gh pr create --base "$BASE" --head "$HEAD" --title "PR: $BASE to $HEAD" --body "Changes between $BASE and $HEAD."
  fi
done

echo "Pull request creation completed!"
