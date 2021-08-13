
from openstack import block_storage
from collector_api_base import CollectorAPIBase
from resources_block_storage import Service
from resources_dummy import DummyApiVersions1Up

import logging
logger = logging.getLogger(__name__)

class CollectorAPIBlockStorage(CollectorAPIBase):
    def __init__(
            self,
            config,
            os,
            metrics,
            api_name,
            project_name,
            name_prefix
            ):
        super().__init__(config, os, metrics, api_name, project_name, name_prefix, [DummyApiVersions1Up])


    def collectMicroServiceState(self):
        services = []
        for service in self.os.block_storage._list(Service):
            services.append({'binary': service.binary, 'host': service.host, 'status': service.status, 'state': service.state})
        self._updateMicroServiceMetrics(services)

