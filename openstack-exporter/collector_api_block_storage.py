"""
Volume / Cinder collector
"""
import logging
#from openstack import block_storage
from collector_api_base import CollectorAPIBase
from resources_block_storage import Service
from resources_dummy import DummyApiVersions1Up

LOGGER = logging.getLogger(__name__)

class CollectorAPIBlockStorage(CollectorAPIBase):
    """
    Cinder
    """
    # pylint: disable=fixme, too-many-arguments
    def __init__(
            self,
            config,
            openstack,
            metrics,
            api_name,
            project_name,
            name_prefix
        ):
        self.data = {}
        super().__init__(config, openstack, metrics, api_name, project_name, name_prefix,
                         [DummyApiVersions1Up])


    def collect_micro_service_state(self):
        services = []
        for service in self.openstack.block_storage._list(Service):
            services.append({'binary': service.binary, 'host': service.host,
                             'status': service.status, 'state': service.state})
        self._update_micro_service_metrics(services)
