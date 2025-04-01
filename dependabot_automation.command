#!/bin/bash

# Dependabot Automation Command
# This script runs the dependabot_automation.py script to automate handling of Dependabot alerts

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Run the Python script
python3 ./dependabot_automation.py "$@"
