#!/bin/bash

echo "Executing create_pkg.sh..."

cd $path_cwd
cd src

# Installing python dependencies...
FILE=$path_cwd/src/requirements.txt
echo "Requirements file: $FILE"
cat $FILE
if [ -f "$FILE" ]; then
  echo "Installing dependencies..."
  pip install -r "$FILE" -t . --platform manylinux2014_x86_64 --only-binary=:all: --python-version 3.10 --implementation cp
  # Also install pure-python packages without platform constraint
  pip install -r "$FILE" -t . --upgrade --no-deps 2>/dev/null || true
else
  echo "Error: requirements.txt does not exist!"
fi

echo "Finished script execution!"