#!/bin/bash

export FLASK_APP=app.py
CURRENT_TIME=$(date +%s)
flask db migrate -m "${CURRENT_TIME}"
flask db upgrade