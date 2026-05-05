#!/usr/bin/env bash
set -euo pipefail

git pull --ff-only
./scripts/run.sh
