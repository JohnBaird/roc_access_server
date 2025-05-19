#!/bin/bash
source /home/roc/.bash_profile
cd /home/roc/roc_access_server
source ./venv/bin/activate
python main.py
deactivate
