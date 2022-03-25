#!/usr/bin/python3

"""
Prometheus Openstack Exporter, collect openstack api metrics and export them on web site where prometheus can poll them. 
"""

import os
import sys
import logging
import traceback
import threading
import time
import queue
import schedule
from prometheus_client import start_http_server

from collector import Collector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s:%(levelname)s:%(message)s"
    )

LOGGER = logging.getLogger(__name__)

def get_config():
    """
    Get config from environment
    """

    configuration = {}

    # check that mandatory openstack environment variables are present
    # we don't read them into config since openstacksdk get's them directly from the environment
    # pylint: disable=fixme, line-too-long
    for param in ['OS_AUTH_URL', 'OS_PROJECT_NAME', 'OS_USERNAME', 'OS_PASSWORD', 'OS_REGION_NAME', 'OS_USER_DOMAIN_NAME', 'OS_PROJECT_DOMAIN_NAME']:
        LOGGER.debug(os.environ)
        if not os.getenv(param, default=False):
            LOGGER.error('Environment variable %s is not defined', param)
            sys.exit(1)

    # coma separated list of api to be ignored in polling
    configuration['api-exclude'] = os.getenv('OS_EXPORTER_API_EXCLUDE', default="").split(',')
    configuration['listen-port'] = os.getenv('OS_EXPORTER_LISTEN_PORT', default=9103)
    configuration['metric_prefix'] = os.getenv('OS_EXPORTER_METRIC_PREFIX', default='openstack')
    configuration['interval'] = os.getenv('OS_EXPORTER_INTERVAL_SECONDS', default='60')

    return configuration


if __name__ == '__main__':

    CONFIG = get_config()

    # metrics server that can be polled by prometheus
    start_http_server(CONFIG['listen-port'])

    COLLECTOR = Collector(CONFIG)

    # we use schedule library with threads to make sure it runs at regular intervals 
    # see: https://schedule.readthedocs.io/en/stable/parallel-execution.html
    # we use only one threads for the jobs:
    # - no need to check if all libs are thread save
    # - do not overload the prodcution cloud when it get's slow for some reason.

    # setup job queue and start thread working on it.
    JOB_QUEUE = queue.Queue()
    # pylint: disable=fixme, missing-function-docstring
    def execute_jobs_in_queue():
        while True:
            job_func = JOB_QUEUE.get()
            job_func()
            JOB_QUEUE.task_done()
            # we let uncaught exceptions go. They will stop the WORKER_THREAD thread.
            # The main thread can detect that and will then exit the program

    WORKER_THREAD = threading.Thread(target=execute_jobs_in_queue)
    WORKER_THREAD.start()

    def job():
        """
        have scheduler put jobs into queue in regular intervals forever
        Note: we only have a single thread -> make sure the interval is not shorter
        than the time needed to collect the data.
        """
        COLLECTOR.refresh()
        LOGGER.info("job done")
    schedule.every(int(CONFIG['interval'])).seconds.do(JOB_QUEUE.put, job)

    # run immediately (the scheduler schedules the first run only after one interval)
    try:
        job()
    # pylint: disable=fixme, bare-except
    except:
        # pylint: disable=fixme, line-too-long
        LOGGER.error("Unhandled exception during data collection, we have to abort. The openstack-exporter probably needs improved error handling...")
        LOGGER.error(traceback.format_exc())
        sys.exit(3)
    while True:
        LOGGER.debug("Jobqueue length: {}".format(len(JOB_QUEUE.queue)))
        if len(JOB_QUEUE.queue) > 1:
            # we are scheduling jobs faster than they can run in a single thread -> we drop one
            LOGGER.info("dropping one job from schedulers jobqueue.")
            JOB_QUEUE.get()
        if not WORKER_THREAD.is_alive():
            # this may happen if there is an uncaught exception in a job.
            LOGGER.error("WORKER_THREAD is dead. Exiting...")
            sys.exit(2)
        schedule.run_pending()
        time.sleep(1)
