"""
Volume / Cinder collector
"""
import datetime
import logging
from prometheus_client import Gauge
from collector_api_base import CollectorAPIBase
from resources_block_storage import Service
from resources_dummy import DummyApiVersions1Up
from resources_volumes import Volume

LOGGER = logging.getLogger(__name__)
VOLUMES_WRONG_STATE_WAIT_TIME = datetime.timedelta(minutes=5)

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

    def init_metrics(self):
        self.data['volumes'] = {}
        self.metrics['volumes'] = Gauge(
            self.name_prefix + 'volumes', '', ['status'])

    def collect_micro_service_state(self):
        services = []
        for service in self.openstack.block_storage._list(Service):
            services.append({'binary': service.binary, 'host': service.host,
                             'status': service.status, 'state': service.state})
        self._update_micro_service_metrics(services)

    def collect_api_specific_data(self):
        # volumes
        data = {}
        for status in self.data['volumes']:
            data[status] = 0
        for volume in self.openstack.block_storage._list(Volume, base_path="/volumes/detail",
                                                         all_projects=True):
            if (volume.status != "in-use" and volume.status != "available"):
                if datetime.datetime.strptime(volume.updated_at, "%Y-%m-%dT%H:%M:%S.000000") + VOLUMES_WRONG_STATE_WAIT_TIME < datetime.datetime.now():
                    LOGGER.warning("Volume %s in project %s stuck in status %s since %s",
                                   volume.id, volume.project_id, volume.status, volume.updated_at)
            if not volume.status in data:
                data[volume.status] = {}
                data[volume.status] = 0
            data[volume.status] += 1
        for status in data:
            self.metrics['volumes'].labels(status).set(data[status])
        self.data['volumes'] = data
        LOGGER.debug(data)
