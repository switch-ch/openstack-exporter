"""
Base Class for Openstack API collectors
"""
import logging
import traceback
from resources_dummy import DummyApiVersions, DummyApiVersions1Up, DummyApiVersions2Up

LOGGER = logging.getLogger(__name__)

# pylint: disable=fixme, too-many-instance-attributes
class CollectorAPIBase():
    """
    Base class for openstack collectors, can also be used directly if only API 
    availability is needed.
    """
    # pylint: disable=fixme, too-many-arguments
    def __init__(
            self,
            config,
            openstack,
            metrics,
            api_name,
            project_name,
            name_prefix,
            api_check_resources = (DummyApiVersions, DummyApiVersions1Up, DummyApiVersions2Up)
        ):
        self.config = config
        self.openstack = openstack
        self.metrics = metrics
        self.api_name = api_name
        self.project_name = project_name
        self.initialized = False
        self.name_prefix = name_prefix + api_name.replace("-", '_') + "_"
        self.api_check_resources = api_check_resources
        self.seen_microservices = {}
        self.state_is_up = False
        self.init()


    def init_metrics(self):
        """
        init collector specific prometheus metrics
        """

    def get_api_version(self):
        """
        get API Versions, this works even when api is down
        """
        try:
            LOGGER.debug("Get API version for: {}({})".format(self.api_name, self.project_name))
            for version in self.openstack.config.get_all_version_data(self.api_name):
                if version.status == "CURRENT":
                    self.metrics['api_info'].labels(self.api_name).info({
                        'status': str(version.status),
                        'version': str(version.version),
                        'min_microversion': str(version.min_microversion),
                        'max_microversion': str(version.max_microversion)
                        })
                    LOGGER.debug(version)
        # pylint: disable=fixme, broad-except
        except Exception:
            LOGGER.error(traceback.format_exc())

    def init(self):
        """
        init part that can be overridden
        """
        self.init_metrics()
        self.get_api_version()

        # force instatiation of proxy
        if not self.api_name in self.openstack._proxies:
            try:
                eval("self.openstack." + self.api_name.replace("-", '_'))
                LOGGER.info("Instantiated proxy for: {}({})".format(self.api_name, self.project_name))
                self.initialized = True

                self._prometheus_counter = self.openstack._proxies[self.api_name]._prometheus_counter
                self._prometheus_histogram = self.openstack._proxies[self.api_name]._prometheus_histogram
            # pylint: disable=fixme, broad-except
            except Exception:
                # no need to do anything, this will be retried on next run
                LOGGER.info("Could not initialize proxy for {}({})".
                            format(self.api_name, self.project_name))


    def get_api_state(self):
        """
        get the current state of openstack api/endpoint
        """
        self.state_is_up = False
        state = "down"

        if self.initialized:
            LOGGER.debug("Check API status for {}".format(self.api_name))
            for resource in self.api_check_resources:
                try:
                    self.openstack._proxies[self.api_name]._get(resource, requires_id=False)
                    state = "up"
                    self.state_is_up = True
                # pylint: disable=fixme, bare-except
                except:
                    # state is already initialized to 'down'
                    pass

        self.metrics['api_state'].labels(self.api_name).state(state)

    def _update_micro_service_metrics(self, services):
        current = {}
        for service in services:
            item = (self.api_name, service['binary'], service['host'])
            current[item] = 1
            LOGGER.debug(service)
            LOGGER.debug("Checking Microservices status for: {} - {} {} {} {}".
                         format(self.api_name, service['binary'], service['host'],
                                service['status'], service['state']))
            self.metrics['service_state'].labels(*list(item)).state(service['state'])
            self.metrics['service_status'].labels(*list(item)).state(service['status'])

        # remove microservices that are gone
        for item in self.seen_microservices:
            if not item in current:
                LOGGER.debug("Deleting micro service: {}-{}-{}".format(*list(item)))
                self.savely_remove_labels('service_state', item)
                self.savely_remove_labels('service_status', item)
        self.seen_microservices = current


    def collect_micro_service_state(self):
        """
        collect the status of sub services belonging to the api. E.g. For Nova API we have
        microservices like nova-scheduler, nova-compute, etc
        """

    def collect_api_specific_data(self):
        """
        collect data specific to each collector
        """

    def collect(self):
        """
        get current value of all metrics
        """
        if not self.initialized:
            self.init()
        self.get_api_state()
        if  self.state_is_up:
            self.collect_micro_service_state()
            self.collect_api_specific_data()

    def savely_remove_labels(self, metric, label_values):
        """
        for some metrics, it is important to remove label value sets that are not longer present
        in the cloud. The prometheus library does not do this automatically for counter no longer 
        being updated.
        """
        try:
            labels = list(label_values)
            labels = labels[0:len(self.metrics[metric]._labelnames)]
            self.metrics[metric].remove(*labels)
        # pylint: disable=fixme, broad-except
        except Exception as exc:
            LOGGER.debug("Error removing metric: %s(%s): %s", metric, str(label_values), str(exc))

    def disable_stats_collection(self, api_name=None):
        """
        disable statistics collection on openstack api calls, when you want those calls not to 
        affect your statistics
        """
        if not api_name:
            api_name = self.api_name
        self.openstack._proxies[api_name]._prometheus_counter = None
        self.openstack._proxies[api_name]._prometheus_histogram = None

    def enable_stats_collection(self, api_name=None):
        """
        reenable stats collection on an openstack api
        """
        if not api_name:
            api_name = self.api_name
        self.openstack._proxies[api_name]._prometheus_counter = self._prometheus_counter
        self.openstack._proxies[api_name]._prometheus_histogram = self._prometheus_histogram
