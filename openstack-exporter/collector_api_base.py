
import traceback
from resources_dummy import DummyApiVersions, DummyApiVersions1Up, DummyApiVersions2Up

import logging
logger = logging.getLogger(__name__)

class CollectorAPIBase(object):
    def __init__(
            self,
            config,
            os,
            metrics,
            api_name,
            project_name,
            name_prefix,
            api_check_resources = (DummyApiVersions, DummyApiVersions1Up, DummyApiVersions2Up)
            ):
        self.config = config
        self.os = os
        self.metrics = metrics
        self.api_name = api_name
        self.project_name = project_name
        self.initialized = False
        self.name_prefix = name_prefix + api_name.replace("-", '_') + "_"
        self.api_check_resources = api_check_resources
        self.seen_microservices = {}
        self.init()


    def initMetrics(self):
        pass
    
    def getApiVersion(self):
        # get API Versions, this works even when api is down
        try:
            logger.debug("Get API version for: {}({})".format(self.api_name, self.project_name))
            for version in self.os.config.get_all_version_data(self.api_name):
                if version.status == "CURRENT":
                    self.metrics['api_info'].labels(self.api_name).info({
                            'status': str(version.status), 
                            'version': str(version.version), 
                            'min_microversion': str(version.min_microversion), 
                            'max_microversion': str(version.max_microversion)
                            })
                    logger.debug(version)
        except Exception:
            logger.error(traceback.format_exc())

    def init(self):
        self.initMetrics()
        self.getApiVersion()

        # force instatiation of proxy
        if not self.api_name in self.os._proxies:
            try:
                eval("self.os." + self.api_name.replace("-", '_'))
                logger.info("Instantiated proxy for: {}({})".format(self.api_name, self.project_name))
                self.initialized = True

                self._prometheus_counter = self.os._proxies[self.api_name]._prometheus_counter
                self._prometheus_histogram = self.os._proxies[self.api_name]._prometheus_histogram
            except Exception:
                # no need to do anything, this will be retried on next run
                logger.info("Could not initialize proxy for {}({})".format(self.api_name, self.project_name))


    def getAPIState(self):
        self.stateIsUp = False
        state = "down"

        if self.initialized:
            logger.debug("Check API status for {}".format(self.api_name))
            for resource in self.api_check_resources:
                try:
                    self.os._proxies[self.api_name]._get(resource, requires_id=False)
                    state = "up"
                    self.stateIsUp = True
                except:
                    # state is already initialized to 'down'
                    pass
    
        self.metrics['api_state'].labels(self.api_name).state(state)

    def _updateMicroServiceMetrics(self, services):
        current = {}
        for service in services:
            item=(self.api_name, service['binary'], service['host'])
            current[item] = 1
            logger.debug (service)
            logger.debug("Checking Microservices status for: {} - {} {} {} {}".format(self.api_name, service['binary'], service['host'], service['status'], service['state']))
            self.metrics['service_state'].labels(*list(item)).state(service['state'])
            self.metrics['service_status'].labels(*list(item)).state(service['status'])

        # remove microservices that are gone
        for item in self.seen_microservices:
            if not item in current:
                logger.debug("Deleting micro service: {}-{}-{}".format(*list(item)))
                self.savely_remove_labels('service_state', item)
                self.savely_remove_labels('service_status', item)
        self.seen_microservices = current


    # collect the status of sub services belonging to the api. E.g. For Nova API we have microservices like nova-scheduler, nova-compute, etc
    def collectMicroServiceState(self):
        pass

    # collect data specific to each collector
    def collectApiSpecificData(self):
        pass

    def collect(self):
        if not self.initialized:
            self.init()
        self.getAPIState()
        if  self.stateIsUp:
            self.collectMicroServiceState()
            self.collectApiSpecificData()

    # for some metrics, it is important to remove label value sets that are not longer present in the cloud.
    # the prometheus library does not do this automatically for counter no longer being updated.
    def savely_remove_labels(self, metric, label_values):
        try:
            labels = list(label_values)
            labels = labels[0:len(self.metrics[metric]._labelnames)]
            self.metrics[metric].remove(*labels)
        except Exception as e:
            logger.debug("Error removing metric: %s(%s): %s", metric, str(label_values), str(e))

    def disable_stats_collection(self, api_name=None):
        if not api_name:
            api_name = self.api_name
        self.os._proxies[api_name]._prometheus_counter = None        
        self.os._proxies[api_name]._prometheus_histogram = None    

    def enable_stats_collection(self, api_name=None):
        if not api_name:
            api_name = self.api_name
        self.os._proxies[api_name]._prometheus_counter = self._prometheus_counter        
        self.os._proxies[api_name]._prometheus_histogram = self._prometheus_histogram
