


## Start Celery
```shell
celery -A app.celery_tasks.celery_app worker --loglevel=info --concurrency=2 -Q tpl_detection_tasks
```

## Docker
### build
docker-compose -f compose/docker-compose-all.yml build

### up
docker-compose -f compose/docker-compose-all.yml up -d