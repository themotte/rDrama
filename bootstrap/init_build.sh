#!/bin/bash
set -euxo pipefail

cd ./chat
yarn install
yarn chat
cd ..
