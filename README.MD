# Enqueter API

## Overview
API for Enqueter project.

`Development environment`
* MacOS (Bigsur)
* InteliJ IDEA (python community edition)
* python3.9.6 (flask)

## Setup
<u>1. venv</u>
```bash
# Create
$ python3 -m venv [ENV_NAME]
# Start
$ . .venv/bin/activate
# Shutdown
(.venv)$ deactivate
# Clear
$ rm -rf ENV_NAME/
# Reset
$ python3 -m venv -clear ENV_NAME
```

<u>2. pip</u>
```bash
# Install libraries
(.venv)$ pip install --upgrade pip
(.venv)$ pip install -r requirements.txt
# Get list of installed libraries
(.venv)$ pip list
(.venv)$ pip freeze
# Output to requirements.txt
(.venv)$ pip freeze > requirements.txt
```

<u>3. Start app</u>
```bash
(.venv)$ python app.py
```