#!/usr/bin/env bash

OS=$(uname -s)
echo $OS

if [ "$OS" = "Darwin" ]; then
  DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
else
  full_path=$(realpath $0)
  DIR=$(dirname $full_path)
fi

echo $DIR
cd $DIR && docker-compose down && docker-compose up --build -d
