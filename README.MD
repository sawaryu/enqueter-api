# Enqueter API

## Overview

API for Enqueter project.

`Development environment`

* MacOS (Bigsur)
* InteliJ IDEA (python community edition)
* python(3.9.6)
* flask(2.0.2)

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

<u>3. Migration</u>

`Initial`

```bash
# Create files for migration
(.venv)$ flask db init
# Fill the difference between Current status and Models in code. Add alembic_version table.
# (* At this point, you should deploy this modification.)
(.venv)$ flask db migrate -m "initial"
# Execute migration
# (* You should also do this operation in production env) 
(.venv)$ flask db upgrade
```

`Thereafter`

```bash
# Add file to `migrations`dir
# (* At this point, you should deploy this modification.)
(.venv)$ flask db migrate -m "sample"
# Reflect modification to DB 
# (* You should also do this operation in production env) 
(.venv)$ flask db upgrade
```

<u>4. Start app</u>

```bash
(.venv)$ python app.py
```