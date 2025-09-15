# BLADE

A multi-agent C/C++ binary TPL detection framework.

## Requirements
- MacOS 13+/Ubuntu 20.04+
- Python 3.11+
- Docker

## Quick Start
### 1. Clone the Repository
### 2. Install Python Dependencies

```shell    
pip install -r requirements.txt
```

### 3. Prepare Database
#### 3.1. Install PostgreSQL by Docker
```shell
docker-compose -f compose/docker-compose-db.yml up -d
```

#### 3.2. Import Database Schema and data
```shell
docker exec -i bsca_data_1_0_5 psql -U tpl_data -d tpl_data < tpl_data_1.0.5_20250805.sql
```
### 4. Config environment variables by `.env` file

### 5. Run Demo

Single file detection:
```bash
python detect.py -i /path/to/binary -o result.json
```

Batch detection:
```bash
python detect.py -i file1 file2 file3 -o results.json
```

Batch detection with file list:
```bash
python detect.py --file-list files.txt -o results.json
```


Use `python detection_script.py -h` for detailed help.

## Usage Instructions

### Use API
Docs TO BE DONE

#### Start Celery
```shell
celery -A app.celery_tasks.celery_app worker --loglevel=info --concurrency=2 -Q tpl_detection_tasks
```

### Use API with Docker
Docs TO BE DONE

### build
docker-compose -f compose/docker-compose-all.yml build

### up
docker-compose -f compose/docker-compose-all.yml up -d

### USE SDK
Docs TO BE DONE