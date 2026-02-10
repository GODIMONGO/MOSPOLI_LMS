web: gunicorn --worker-class gthread --threads ${GUNICORN_THREADS:-8} -w ${WEB_CONCURRENCY:-2} --bind 0.0.0.0:$PORT main:app
worker: dramatiq tasks routes.input_file --processes ${DRAMATIQ_PROCESSES:-2} --threads ${DRAMATIQ_THREADS:-4}
