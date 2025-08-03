


## Start Celery
```shell
celery -A app.celery_tasks.celery_app worker --loglevel=info --concurrency=2 -Q tpl_detection_tasks
```
