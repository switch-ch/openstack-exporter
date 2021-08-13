
from openstack import resource


class Service(resource.Resource):
    resource_key = 'service'
    resources_key = 'services'
    base_path = '/os-services'

    # capabilities
    allow_list = True
    allow_commit = True

    # Properties
    #: Status of service
    status = resource.Body('status')
    #: State of service
    state = resource.Body('state')
    #: Name of service
    binary = resource.Body('binary')
    #: Id of service
    id = resource.Body('id')
    #: Disabled reason of service
    disables_reason = resource.Body('disabled_reason')
    #: Host where service runs
    host = resource.Body('host')
    #: The availability zone of service
    availability_zone = resource.Body("zone")

