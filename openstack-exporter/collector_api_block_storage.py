"""
Volume / Cinder collector
"""
import datetime
import logging
from prometheus_client import Gauge, Enum
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
        operating_statuses = ['CREATING', 'AVAILABLE', 'RESERVED', 'ATTACHING', 'DETACHING', 'IN-USE', 'MAINTENANCE', 'DELETING', 'AWAITING-TRANSFER', 'ERROR', 'ERROR_DELETING', 'BACKING-UP', 'RESTORING-BACKUP', 'ERROR_BACKING-UP', 'ERROR_RESTORING', 'ERROR_EXTENDING', 'DOWNLOADING', 'UPLOADING', 'RETYPING', 'EXTENDING']
        self.data['volumes'] = {}
        self.metrics['volumes'] = Gauge(
            self.name_prefix + 'volumes', '', ['status'])
        volume_labels = ['id', 'name', 'project_id']
        self.metrics['volume_status'] = Enum(
            self.name_prefix + 'volume_status', '', volume_labels, states=operating_statuses)

    def collect_micro_service_state(self):
        services = []
        for service in self.openstack.block_storage._list(Service):
            services.append({'binary': service.binary, 'host': service.host,
                             'status': service.status, 'state': service.state})
        self._update_micro_service_metrics(services)

    def collect_api_specific_data(self):
        # volumes
        current = {}
        for volume in self.openstack.block_storage._list(Volume, base_path="/volumes/detail", all_projects=True):
            item = (volume.id, volume.name, volume.project_id)
            current[item] = 1
            self.metrics['volume_status'].labels(*list(item)).state(volume.status.upper())

        # Remove volumes which are no longer present
        for item in self.data['volumes']:
            if item not in current:
                LOGGER.debug("Removing non-existing volume: {}".format(item))
                self.savely_remove_labels('volume_status', item)
        self.data['volumes'] = current
