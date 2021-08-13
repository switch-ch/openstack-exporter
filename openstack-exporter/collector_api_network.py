
from prometheus_client import Gauge
from collector_api_base import CollectorAPIBase
from resources_dummy import DummyApiVersions

import logging
logger = logging.getLogger(__name__)

class CollectorAPINetwork(CollectorAPIBase):
    def __init__(
            self,
            config,
            os,
            metrics,
            api_name,
            project_name,
            name_prefix
            ):
        self.data = {}
        super().__init__(config, os, metrics, api_name, project_name, name_prefix, [DummyApiVersions])


    def collectMicroServiceState(self):
        services = []
        for service in self.os.network.agents():
            if service.is_admin_state_up:
                status = "enabled"
            else:
                status = "disabled"
            if service.is_alive:
                state = "up"
            else:
                state = "down"
            services.append({'binary': service.binary, 'host': service.host, 'status': status, 'state': state})
        self._updateMicroServiceMetrics(services)

    def initMetrics(self):
        self.data['floating_ips'] = {}
        self.metrics['floating_ips'] = Gauge(self.name_prefix + 'floating_ips', '', ['project_id', 'status'])

        self.data['routers'] = {}
        self.metrics['routers'] = Gauge(self.name_prefix + 'routers', '', ['status'])

    def collectApiSpecificData(self):
        # floating ips
        data = {}
        for fip in self.os.network.ips():
            if not fip.project_id in data:
                data[fip.project_id] = {}
            if not fip.status in data[fip.project_id]:
                data[fip.project_id][fip.status] = 0
            data[fip.project_id][fip.status] += 1
            logger.debug("Floating IP; project: {}, status: {}".format(fip.project_id ,fip.status))
        for project in data:
            for status in data[project]:
                self.metrics['floating_ips'].labels(project, status).set(data[project][status])

        # remove stuff that is gone
        for project in self.data['floating_ips']:
            for status in self.data['floating_ips'][project]:
                if not project in data or not status in data[project]:
                    self.savely_remove_labels('floating_ips', (project, status))
        self.data['floating_ips'] = data

        # routers
        data = {}
        for status in self.data['routers']:
            data[status] = 0
        for router in self.os.network.routers():
            if not router.status in data:
                data[router.status] = 0
            data[router.status] += 1
        for status in data:
            self.metrics['routers'].labels(status).set(data[status])
        self.data['routers'] = data