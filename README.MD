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
$ deactivate
# Clear
$ rm -rf ENV_NAME/
# Reset
$ python3 -m venv -clear ENV_NAME
```

<u>2. pip</u>
```bash
# Install libraries
$ pip install --upgrade pip
$ pip install -r requirements.txt
# Get list of installed libraries
$ pip list
$ pip freeze
# Output to requirements.txt
$ pip freeze > requirements.txt
```
<u>3. Start project in Docker</u>
```bash
# Start project (*--no-cache is optional)
(enquter)$ docker-compose build --no-cache
# Execute batch container
$ docker run --rm --net='enqueter_default' --name flask_batch -it \
  -e SQLALCHEMY_DATABASE_URI='mysql+pymysql://production:production@db/production?charset=utf8mb4' enqueter_api sh batch.sh
```

## DB structure
![image](images/db-structure.png)


## Attention
*　Doesn't work complement

Solved by assigning `.venv` as "exclude folder".

![image](images/import-problem.png)