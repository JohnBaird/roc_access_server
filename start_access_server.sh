#!/bin/bash
source /home/user/.bash_profile
cd /home/user/roc_access_server
source ./venv/bin/activate
python main.py
deactivate
