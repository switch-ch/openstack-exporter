from openstack import resource

# dummy resource used to check if something responds to http get request at given endpoint

class DummyApiVersions(resource.Resource):
    base_path = '/'

    # capabilities
    allow_fetch = True

    # we expect a proper http response with some content -> raise exception if nothing usefull came back
    content_type = resource.Header("content-type")

class DummyApiVersions1Up(resource.Resource):
    base_path = '../'

    # capabilities
    allow_fetch = True

    content_type = resource.Header("content-type")

class DummyApiVersions2Up(resource.Resource):
    base_path = '../../'

    # capabilities
    allow_fetch = True

    content_type = resource.Header("content-type")
