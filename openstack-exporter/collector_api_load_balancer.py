
from openstack.exceptions import ResourceNotFound
from collector_api_base import CollectorAPIBase
from resources_dummy import DummyApiVersions1Up
from prometheus_client import Enum, Gauge, Info, Counter

import logging
logger = logging.getLogger(__name__)

class CollectorAPILoadBalancer(CollectorAPIBase):
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
        super().__init__(config, os, metrics, api_name, project_name, name_prefix, [DummyApiVersions1Up])

    def _adminState2String(self, state):
        if state:
            return "enabled"
        else:
            return "disabled"


    def initMetrics(self):

        # one could argue, that the operating_status, admin_status, and provisioning_status should all be the same metric instead of seperate onces for
        # lb, listener, pool etc. 
        # Unfortunately the python prometheus library does not allow for changing sets of labels on the same metric -> we need multiple metrics

        # global
        operating_statuses=['ONLINE', 'DRAINING', 'OFFLINE', 'DEGRADED', 'ERROR', 'NO_MONITOR']
        provisioning_statuses=['ACTIVE', 'DELETED', 'ERROR', 'PENDING_CREATE', 'PENDING_UPDATE', 'PENDING_DELETE']
        admin_statuses=['enabled', 'disabled']

        # load balancers
        self.data['lbs'] = {}
        self.data['lbs_project_id'] = {}
        self.metrics['lb_info'] =                Info(self.name_prefix + 'lb','', ['id'])
        self.data['project_name'] = {}
        lb_labels=['id', 'name', 'project_id']
        self.metrics['lb_operating_status'] =    Enum(self.name_prefix + 'lb_operating_status','', lb_labels, states=operating_statuses)
        self.metrics['lb_admin_status'] =        Enum(self.name_prefix + 'lb_admin_status','', lb_labels, states=admin_statuses)
        self.metrics['lb_provisioning_status'] = Enum(self.name_prefix + 'lb_provisioning_status','', lb_labels, states=provisioning_statuses)

        self.lb_gauges = {
            'lb_active_connections':'active_connections', 
        }
        for measurement in self.lb_gauges:
            self.metrics[measurement] = Gauge(self.name_prefix + measurement, '', lb_labels)

        self.data['lb_counters_current'] = {}
        self.lb_couters = {
            'lb_in_bytes':'bytes_in', 'lb_out_bytes':'bytes_out', 
            'lb_connections':'total_connections',
            'lb_request_errors':'request_errors', 
        }
        for measurement in self.lb_couters:
            self.metrics[measurement] = Counter(self.name_prefix + measurement, '', lb_labels)
            self.data['lb_counters_current'][measurement] = {}

        # listenener
        self.data['listeneners'] = {}
        listener_labels=['id', 'name', 'project_id', 'loadbalancers']
        self.metrics['listener_provisioning_status'] = Enum(self.name_prefix + 'listener_provisioning_status','', listener_labels, states=provisioning_statuses)
        self.metrics['listener_operating_status'] = Enum(self.name_prefix + 'listener_operating_status','', listener_labels, states=operating_statuses)
        self.metrics['listener_admin_status'] =  Enum(self.name_prefix + 'listener_admin_status','', listener_labels, states=admin_statuses)
        self.metrics['listener_connection_limit'] =  Gauge(self.name_prefix + 'listener_connection_limit','', listener_labels)

        # pool
        self.data['pools'] = {}
        self.data['pools_data'] = {}
        self.data['pools_data']['lbs'] = {}
        self.data['pools_data']['listeners'] = {}
        pool_labels=['id', 'name', 'project_id', 'loadbalancers', 'listeners']
        self.metrics['pool_admin_status'] =  Enum(self.name_prefix + 'pool_admin_status','', pool_labels, states=admin_statuses)
        self.metrics['pool_provisioning_status'] = Enum(self.name_prefix + 'pool_provisioning_status','', pool_labels, states=provisioning_statuses)
        self.metrics['pool_operating_status'] = Enum(self.name_prefix + 'pool_operating_status','', pool_labels, states=operating_statuses)

        # member
        self.data['members'] = {}
        member_labels=['id', 'name', 'project_id', 'loadbalancers', 'listeners', 'pool_id']
        self.metrics['member_admin_status'] =  Enum(self.name_prefix + 'member_admin_status','', member_labels, states=admin_statuses)
        self.metrics['member_provisioning_status'] = Enum(self.name_prefix + 'member_provisioning_status','', member_labels, states=provisioning_statuses)
        self.metrics['member_operating_status'] = Enum(self.name_prefix + 'member_operating_status','', member_labels, states=operating_statuses)

        # health monitor
        self.data['hms'] = {}
        hm_labels=['id', 'name', 'project_id', 'loadbalancers', 'listeners', 'pools']
        self.metrics['hm_admin_status'] =  Enum(self.name_prefix + 'hm_admin_status','', hm_labels, states=admin_statuses)
        self.metrics['hm_provisioning_status'] = Enum(self.name_prefix + 'hm_provisioning_status','', hm_labels, states=provisioning_statuses)
        self.metrics['hm_operating_status'] = Enum(self.name_prefix + 'hm_operating_status','', hm_labels, states=operating_statuses)

        # amphorae
        self.data['amphorae'] = {}
        amphora_labels=['id', 'loadbalancer_id', 'project_id']
        self.metrics['amphora_status'] = Enum(self.name_prefix + 'amphora_status','', amphora_labels, 
            states=['BOOTING', 'ALLOCATED', 'READY', 'PENDING_CREATE', 'PENDING_DELETE', 'DELETED', 'ERROR'])
        self.metrics['amphora_role'] = Enum(self.name_prefix + 'amphora_role','', amphora_labels, 
            states=['STANDALONE', 'MASTER', 'BACKUP'])
        self.metrics['amphora_cert_expiration'] = Gauge(self.name_prefix + 'amphora_cert_expiration','', amphora_labels)


    def collectApiSpecificData(self):
        ###################
        # load balancer
        current = {}
        self.data['lbs_project_id'] = {}
        for lb in self.os.load_balancer.load_balancers():
            item=(lb.id, lb.name, lb.project_id)
            current[item] = 1
            self.data['lbs_project_id'][lb.id] = lb.project_id

            project_name = 'none'
            if  lb.project_id in self.data['project_name']:
                project_name = self.data['project_name'][lb.project_id] 
            else:
                self.disable_stats_collection('identity')
                project = self.os.identity.find_project(lb.project_id)
                self.enable_stats_collection('identity')
                if project:
                    self.data['project_name'][lb.project_id] = project.name
                    project_name = project.name

            try:
                self.disable_stats_collection()
                stats = self.os.load_balancer.get_load_balancer_statistics(lb.id)
                self.enable_stats_collection()
            except:
                # It's possible that the lb disapears before retrieving the stats -> we just ignore it then.
                stats = None
                self.enable_stats_collection()
            if stats:
                for measurement, attribute in self.lb_gauges.items():
                    self.metrics[measurement].labels(*list(item)).set(stats[attribute])
                for measurement, attribute in self.lb_couters.items():
                    if item in self.data['lb_counters_current'][measurement]:
                        diff = stats[attribute] - self.data['lb_counters_current'][measurement][item]
                        if diff > 0:
                            # it is possible that counters are reset -> the prometheus lib does not like that.
                            # not sure if ignoreing this fact is the proper thing to do though
                            self.metrics[measurement].labels(*list(item)).inc(diff)
                    else:
                        self.metrics[measurement].labels(*list(item)).inc(0)
                    self.data['lb_counters_current'][measurement][item] = stats[attribute]

                self.metrics['lb_operating_status'].labels(*list(item)).state(lb.operating_status)
                self.metrics['lb_admin_status'].labels(*list(item)).state(self._adminState2String(lb.is_admin_state_up))
                self.metrics['lb_provisioning_status'].labels(*list(item)).state(lb.provisioning_status)
                self.metrics['lb_info'].labels(lb.id).info({
                    'name': lb.name,
                    'project_id': lb.project_id,
                    'project_name': project_name,
                    'vip_address': lb.vip_address,
                    'vip_port_id': lb.vip_port_id,
                })
        # remove lbs which are no longer present
        for item in self.data['lbs']:
            if item not in current:
                logger.debug("Removing lb: {}".format(item))
                self.savely_remove_labels('lb_operating_status', item)
                self.savely_remove_labels('lb_operating_status', item)
                self.savely_remove_labels('lb_admin_status', item)
                self.savely_remove_labels('lb_provisioning_status', item)
                self.savely_remove_labels('lb_info', item)
                for measurement in self.lb_gauges:
                    self.savely_remove_labels(measurement, item)
                for measurement in self.lb_couters:
                    self.savely_remove_labels(measurement, item)
                if item in self.data['lb_counters_current'][measurement]:
                    del self.data['lb_counters_current'][measurement][item]
        self.data['lbs'] = current

        ###################
        # listener
        current = {}
        for listener in self.os.load_balancer.listeners():
            lbs = []
            for lb in listener.load_balancers:
                lbs.append(lb['id'])
            lbs=",".join(lbs)
            item=(listener.id, listener.name, listener.project_id, lbs)
            current[item] = 1

            # we ignore traffic stats for now
            #stats = self.os.load_balancer.get_listener_statistics(listener.id)

            self.metrics['listener_admin_status'].labels(*list(item)).state(self._adminState2String(listener.is_admin_state_up))
            self.metrics['listener_provisioning_status'].labels(*list(item)).state(listener.provisioning_status)
            self.metrics['listener_operating_status'].labels(*list(item)).state(listener.operating_status)
            self.metrics['listener_connection_limit'].labels(*list(item)).set(listener.connection_limit)

        # remove listeneners which are no longer present
        for item in self.data['listeneners']:
            if item not in current:
                logger.debug("Removing listener: {}".format(item))
                self.savely_remove_labels('listener_admin_status', item)
                self.savely_remove_labels('listener_provisioning_status', item)
                self.savely_remove_labels('listener_operating_status', item)
                self.savely_remove_labels('listener_connection_limit', item)
        self.data['listeneners'] = current

        ###################
        # pool
        current = {}
        for pool in self.os.load_balancer.pools():
            lbs = []
            for lb in pool.loadbalancers:
                lbs.append(lb['id'])
            lbs=",".join(lbs)
            listeners = []
            for listener in pool.listeners:
                listeners.append(listener['id'])
            listeners=",".join(listeners)
            item=(pool.id, pool.name, pool.project_id, lbs, listeners)
            current[item] = 1
            self.data['pools_data']['lbs'][pool.id] = lbs
            self.data['pools_data']['listeners'][pool.id] = listeners

            self.metrics['pool_admin_status'].labels(*list(item)).state(self._adminState2String(pool.is_admin_state_up))
            self.metrics['pool_provisioning_status'].labels(*list(item)).state(pool.provisioning_status)
            self.metrics['pool_operating_status'].labels(*list(item)).state(pool.operating_status)

            ###################
            # member
            current_member = {}
            if not pool.id in self.data['members']:
                self.data['members'][pool.id] = {}

            try:
                self.disable_stats_collection()
                for member in self.os.load_balancer.members(pool.id):
                    member_item=(member.id, member.name, pool.project_id, lbs, listeners, pool.id)
                    current_member[member_item] = 1

                    self.metrics['member_admin_status'].labels(*list(member_item)).state(self._adminState2String(member.is_admin_state_up))
                    self.metrics['member_provisioning_status'].labels(*list(member_item)).state(pool.provisioning_status)
                    self.metrics['member_operating_status'].labels(*list(member_item)).state(pool.operating_status)
                self.enable_stats_collection()

            except ResourceNotFound:
                # it is possible that the pool was removed in the meantime -> we ignore the members then.
                self.enable_stats_collection()

            # remove pools which are no longer present
            for member_item in self.data['members'][pool.id]:
                if member_item not in current_member:
                    logger.debug("Removing member: {}".format(member_item))
                    self.savely_remove_labels('member_admin_status', member_item)
                    self.savely_remove_labels('member_provisioning_status', member_item)
                    self.savely_remove_labels('member_operating_status', member_item)
            self.data['members'][pool.id] = current_member


        # remove pools which are no longer present
        for item in self.data['pools']:
            if item not in current:
                logger.debug("Removing pool: {}".format(item))
                self.savely_remove_labels('pool_admin_status', item)
                self.savely_remove_labels('pool_provisioning_status', item)
                self.savely_remove_labels('pool_operating_status', item)

                # also remmove all members in that pool
                if item[0] in self.data['members']:
                    for member_item in self.data['members'][item[0]]:
                        logger.debug("Removing member: {}".format(member_item))
                        self.savely_remove_labels('member_admin_status', member_item)
                        self.savely_remove_labels('member_provisioning_status', member_item)
                        self.savely_remove_labels('member_operating_status', member_item)
                    del self.data['members'][item[0]]

        self.data['pools'] = current


        ###################
        # health monitors
        current = {}
        for hm in self.os.load_balancer.health_monitors():
            pools = []
            lbs = []
            listeners = []

            for pool in hm.pools:
                pools.append(pool['id'])
                lbs.append(self.data['pools_data']['lbs'][pool['id']])
                listeners.append(self.data['pools_data']['listeners'][pool['id']])
            pools=",".join(pools)
            lbs=",".join(lbs)
            listeners=",".join(listeners)            

            item=(hm.id, hm.name, hm.project_id, lbs, listeners, pools)
            current[item] = 1

            if hm.is_admin_state_up:
                admin_status = "enabled"
            else:
                admin_status = "disabled"
            self.metrics['hm_admin_status'].labels(*list(item)).state(admin_status)
            self.metrics['hm_provisioning_status'].labels(*list(item)).state(hm.provisioning_status)
            self.metrics['hm_operating_status'].labels(*list(item)).state(hm.operating_status)

        # remove pools which are no longer present
        for item in self.data['hms']:
            if item not in current:
                logger.debug("Removing health moniter: {}".format(item))
                self.savely_remove_labels('hm_admin_status', item)
                self.savely_remove_labels('hm_provisioning_status', item)
                self.savely_remove_labels('hm_operating_status', item)
        self.data['hms'] = current


        ###################
        # amphorae
        current = {}
        for amphora in self.os.load_balancer.amphorae():

            if amphora.loadbalancer_id in self.data['lbs_project_id']:
                project_id = self.data['lbs_project_id'][amphora.loadbalancer_id]
            else:
                project_id = 'None'
            item=(amphora.id, amphora.loadbalancer_id, project_id)
            current[item] = 1

            self.metrics['amphora_status'].labels(*list(item)).state(amphora.status)
            if amphora.role:
                self.metrics['amphora_role'].labels(*list(item)).state(amphora.role)
            # self.metrics['amphora_cert_expiration'].labels(*list(item)).set(amphora.cert_expiration)

        # remove pools which are no longer present
        for item in self.data['amphorae']:
            if item not in current:
                logger.debug("Removing amphora: {}".format(item))
                self.savely_remove_labels('amphora_status', item)
                self.savely_remove_labels('amphora_role', item)
                # self.savely_remove_labels('amphora_cert_expiration', item)
        self.data['amphorae'] = current

