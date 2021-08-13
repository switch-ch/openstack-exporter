from prometheus_client import Enum, Gauge, Info, Summary
import openstack
import traceback
from collector_api_base import CollectorAPIBase
from collector_api_compute import CollectorAPICompute
from collector_api_network import CollectorAPINetwork
from collector_api_block_storage import CollectorAPIBlockStorage
from collector_api_load_balancer import CollectorAPILoadBalancer
from resources_dummy import DummyApiVersions1Up

import logging
logger = logging.getLogger(__name__)
openstack.enable_logging(debug=False)

class Collector(object):
    def __init__(
            self,
            config
            ):
        self.config = config
        self.name_prefix = config['metric_prefix'] + "_"
        self.initMetrics()
        self.initOS()
        self.initCollectors()

    def initMetrics(self):
        self.metrics = {}

        # api_state
        self.metrics['api_state'] = Enum(self.name_prefix + 'api_state', 'Status of API', ['api'], states=['up', 'down'])

        # api_info
        self.metrics['api_info'] = Info(self.name_prefix + 'api', 'Version information about APIs', labelnames=['api'])

        # service_state
        self.metrics['service_state'] = Enum(self.name_prefix + 'service_state', 'Status of micro-service', 
            ['api', 'micro_service', 'host'], states=['up', 'down'])
        self.metrics['service_status'] = Enum(self.name_prefix + 'service_status', 'Status of micro-service', 
            ['api', 'micro_service', 'host'], states=['enabled', 'disabled'])

        # collection_time
        self.metrics['collection_duration'] = Summary(self.name_prefix + 'collection_duration_seconds', 
            'Time spend collecting all data', 
            ['api'])

        # collection_time
        self.metrics['collection_timestamp'] = Gauge(self.name_prefix + 'collection_timestamp', 'Timestamp of last successfull collection run')

    def initOS(self):
        # open connection
        self.os = openstack.connect(app_name="openstack-exporter", app_version="0.1")

        # when adding services (proxy) by string instead of class, then openstack sdk uses some generic service-description and proxy
        # all the necessary info is taken from the catalog
        self.os.add_service("cloudformation")


    def initCollectors(self):
        self.collectors = {}
        for service in self.os.list_services():
            if not service.name in self.config['api-exclude']:
                # normalize service_type name
                service_type = self.os.config.get_service_type(service['service_type'])
                if not service_type in self.collectors:
                    if service_type == 'compute':
                        self.collectors[service_type] = CollectorAPICompute(self.config, self.os, self.metrics, service_type, service.name, self.name_prefix)
                    elif service_type == 'block-storage':
                        self.collectors[service_type] = CollectorAPIBlockStorage(self.config, self.os, self.metrics, service_type, service.name, self.name_prefix)
                    elif service_type == 'image':
                        self.collectors[service_type] = CollectorAPIBase(self.config, self.os, self.metrics, service_type, service.name, self.name_prefix, [DummyApiVersions1Up])
                    elif service_type == 'network':
                        self.collectors[service_type] = CollectorAPINetwork(self.config, self.os, self.metrics, service_type, service.name, self.name_prefix)
                    elif service_type == 'load-balancer':
                        self.collectors[service_type] = CollectorAPILoadBalancer(self.config, self.os, self.metrics, service_type, service.name, self.name_prefix)
                    elif service_type == 'cloudformation':
                        self.collectors[service_type] = CollectorAPIBase(self.config, self.os, self.metrics, service_type, service.name, self.name_prefix, [DummyApiVersions1Up])
                    else:
                        self.collectors[service_type] = CollectorAPIBase(self.config, self.os, self.metrics, service_type, service.name, self.name_prefix)

    def refresh(self):
        for api_name, collector in self.collectors.items():
            with self.metrics['collection_duration'].labels(api_name).time():
                try:
                    collector.collect()
                except:
                    logger.error("Unhandled exception during data collection in the {} collector.".format(api_name))
                    logger.error(traceback.format_exc())

        self.metrics['collection_timestamp'].set_to_current_time()

