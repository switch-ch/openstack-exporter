"""
Compute / Nova collector
"""
import json
import logging
from prometheus_client import Gauge, Info, Enum
from collector_api_base import CollectorAPIBase
from resources_dummy import DummyApiVersions


LOGGER = logging.getLogger(__name__)

class CollectorAPICompute(CollectorAPIBase):
    """
    Nova
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
        self.host_measurements = {
            'vcpus':'vcpus', 'vcpus_used':'vcpus_used',
            'running_vms':'running_vms',
            'ram_used_bytes':'memory_used', 'ram_size_bytes':'memory_size', 'ram_free_bytes':'memory_free',
            'local_disk_size_bytes':'local_disk_size', 'local_disk_used_bytes':'local_disk_used', 'local_disk_free_bytes':'local_disk_free',
            'disk_available_bytes':'disk_available',
            'current_workload':'current_workload',
        }
        self.data = {}
        super().__init__(config, openstack, metrics, api_name, project_name, name_prefix,
                         [DummyApiVersions])


    def init_metrics(self):
        for measurement in self.host_measurements:
            self.metrics[measurement] = Gauge(
                self.name_prefix + measurement, '', ['host', 'name', 'aggregates'])

        self.metrics['hypervisor_state'] = Enum(
            self.name_prefix + 'hypervisor_state', '', ['host', 'name', 'aggregates'],
            states=['up', 'down'])
        self.metrics['hypervisor_status'] = Enum(
            self.name_prefix + 'hypervisor_status', '', ['host', 'name', 'aggregates'],
            states=['enabled', 'disabled'])
        self.metrics['hypervisor_info'] = Info(
            self.name_prefix + 'hypervisor', '', ['host'])
        self.metrics['aggregates_info'] = Info(
            self.name_prefix + 'aggregates', '', ['name'])
        self.data['aggregates'] = {}
        self.data['hosts'] = {}


    def collect_micro_service_state(self):
        services = []
        for service in self.openstack.compute.services():
            LOGGER.debug (service)
            services.append({'binary': service.binary, 'host': service.host,
                             'status': service.status, 'state': service.state})
        self._update_micro_service_metrics(services)

    def collect_api_specific_data(self):
        aggregates = {}
        current = {}
        for aggregate in self.openstack.compute.aggregates():
            if not aggregate.deleted: 
                item = (aggregate.name)
                current[item] = 1
                self.metrics['aggregates_info'].labels(aggregate.name).info(
                    {'id': str(aggregate.id), 'hosts': ",".join(aggregate.hosts)})
                for hypervisor in aggregate.hosts:
                    if not hypervisor in aggregates:
                        aggregates[hypervisor] = aggregate.name
                    else:
                        aggregates[hypervisor] = aggregates[hypervisor] + "," + aggregate.name

        for item in self.data['aggregates']:
            if item not in current:
                self.savely_remove_labels('aggregates_info', item)
        self.data['aggregates'] = current

        current = {}
        for hypervisor in self.openstack.compute.hypervisors(details=True):
            host = hypervisor.name.split('.')[0]
            if host in aggregates:
                item=(host, hypervisor.name, aggregates[host])
            else:
                item=(host, hypervisor.name, 'none')
            current[item] = 1

            for measurement, attribute in self.host_measurements.items():
                if measurement.endswith("_bytes"):
                    self.metrics[measurement].labels(*list(item)).set(hypervisor[attribute] * 1048576)
                else:
                    self.metrics[measurement].labels(*list(item)).set(hypervisor[attribute])
            cpu_info = hypervisor.cpu_info
            if not isinstance(cpu_info, dict):
                cpu_info = json.loads(cpu_info)

            self.metrics['hypervisor_state'].labels(*list(item)).state(hypervisor.state)
            self.metrics['hypervisor_status'].labels(*list(item)).state(hypervisor.status)
            self.metrics['hypervisor_info'].labels(host).info({
                'name': str(hypervisor.name), 
                'aggregates': str(aggregates[host]), 
                'arch': str(cpu_info['arch']), 
                'model': str(cpu_info['model']),
                'ip': str(hypervisor.host_ip),
                'vcpus': str(hypervisor.vcpus),
                'ram_gb': str(hypervisor.memory_size),
                'disk_gb': str(hypervisor.local_disk_size),
            })

        # remove host items which are no longer present
        for item in self.data['hosts']:
            if item not in current:
                for measurement in self.host_measurements:
                    self.savely_remove_labels(measurement, item)
                self.savely_remove_labels('hypervisor_state', item)
                self.savely_remove_labels('hypervisor_status', item)
                self.savely_remove_labels('hypervisor_info', item)
        self.data['hosts'] = current
