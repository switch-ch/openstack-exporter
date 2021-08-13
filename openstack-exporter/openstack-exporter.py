#!/usr/bin/python3

import os
import sys
import logging
import traceback
from prometheus_client import start_http_server
import threading
import time
import schedule
import queue

from collector import Collector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s:%(levelname)s:%(message)s"
    )
logger = logging.getLogger(__name__)

def getConfig():
    config = {}

    # check that mandatory openstack environment variables are present
    # we don't read them into config since openstacksdk get's them directly from the environment
    for param in ['OS_AUTH_URL', 'OS_PROJECT_NAME', 'OS_USERNAME', 'OS_PASSWORD', 'OS_REGION_NAME', 'OS_USER_DOMAIN_NAME', 'OS_PROJECT_DOMAIN_NAME']:
        logging.debug(os.environ)
        if not os.getenv(param, default=False): 
            logging.error('Environment variable ' + param + ' is not defined')
            sys.exit(1)

    # coma separated list of api to be ignored in polling
    config['api-exclude'] = os.getenv('OS_EXPORTER_API_EXCLUDE', default="").split(',')
    config['listen-port'] = os.getenv('OS_EXPORTER_LISTEN_PORT', default=9103)
    config['metric_prefix'] = os.getenv('OS_EXPORTER_METRIC_PREFIX', default='openstack')
    config['interval'] = os.getenv('OS_EXPORTER_INTERVAL_SECONDS', default='60')

    return config


if __name__ == '__main__':

    config = getConfig()

    # metrics server that can be polled by prometheus
    start_http_server(config['listen-port'])

    collector = Collector(config)

    # we use schedule library with threads to make sure it runs at regular intervals 
    # see: https://schedule.readthedocs.io/en/stable/parallel-execution.html
    # we use only one threads for the jobs:
    # - no need to check if all libs are thread save
    # - do not overload the prodcution cloud when it get's slow for some reason.

    # setup job queue and start thread working on it.
    jobqueue = queue.Queue()
    def execute_jobs_in_queue():
        while True:
            job_func = jobqueue.get()
            job_func()
            jobqueue.task_done()
            # we let uncaught exceptions go. They will stop the worker_thread thread.
            # The main thread can detect that and will then exit the program

    worker_thread = threading.Thread(target=execute_jobs_in_queue)
    worker_thread.start()

    # have scheduler put jobs into queue in regular intervals forever
    # Note: we only have a single thread -> make sure the interval is not shorter than the time needed to collect the data.
    def job():
        collector.refresh()
        logger.info("job done")
    schedule.every(int(config['interval'])).seconds.do(jobqueue.put, job)

    # run immediately (the scheduler schedules the first run only after one interval)
    try:
        job()
    except:
        logger.error("Unhandled exception during data collection, we have to abort. The openstack-exporter probably needs improved error handling...")
        logger.error(traceback.format_exc())
        sys.exit(3)
    while True:
        logger.debug("Jobqueue length: {}".format(len(jobqueue.queue)))
        if len(jobqueue.queue) > 1:
            # we are scheduling jobs faster than they can run in a single thread -> we drop one
            logger.info("dropping one job from schedulers jobqueue.")
            jobqueue.get()
        if not worker_thread.is_alive():
            # this may happen if there is an uncaught exception in a job.
            logger.error("worker_thread is dead. Exiting...")
            sys.exit(2)
        schedule.run_pending()
        time.sleep(1)
