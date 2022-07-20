# Prometheus Openstack Exporter

There is confustion about api vs service. Unlike openstack documentation, the library calls apis services. This exporter sticks to documentation. APIs are refered to as api not service.
An API is then build using multiple microservices.

e.g.

- API: nova
- Micro Services: nova-compute, nova-api, nova-conductor, nova-scheduler, ...

## Environment

Standard following standard openstack authentication env-variables:
- OS_AUTH_URL
- OS_USERNAME
- OS_PASSWORD
- OS_PROJECT_NAME
- OS_REGION_NAME
- OS_USER_DOMAIN_NAME
- OS_PROJECT_DOMAIN_NAME

Other config parameters:

* LISTEN PORT
  - port to bind to. Default: 9103
* OS_EXPORTER_API_EXCLUDE
  - coma separated list of APIs that should not be polled. Use project name from keystone catalog. E.g. designate not dns... Default: ''
* OS_EXPORTER_INTERVAL_SECONDS
  - how often the exporter should refresh it's data. Default = 60
* OS_EXPORTER_METRIC_PREFIX
  - prometheus metric names prefix. Default = 'openstack'
* OS_EXPORTER_LOG_LEVEL
  - logging level. Must be one of DEBUG, INFO, WARNING or ERROR. Default = "INFO"

## Usage

As of now, no official image is provided. You can build one yourself with:

```bash
  docker build . -t openstack-exporter
```

Launch it with:

```bash
  docker run -ti \
   -e "OS_PROJECT_NAME=my_fancy_project" \
   -e "OS_PASSWORD=change_me" \
   -e "OS_USERNAME=guest" \
   -e "OS_AUTH_URL=https://keystone.cloud.switch.ch/v3" \
   -e "OS_REGION_NAME=regionOne" \
   -e "OS_USER_DOMAIN_NAME=default" \
   -e "OS_PROJECT_DOMAIN_NAME=default" \
  openstack-exporter
```

the default URL with be: http://localhost:9103/


## Development / Test

### Using VSCode

When using Microsoft VSCode then:
- install docker for mac
- install "Remote Containers" extension for vscode
- run the command: `Remote-Containers: Open Folder in Container... ` and open this folder in it.

The first time it'll take a while to open in container, since it'll need to build the docker image first.

To launch the exporter in the debugger, add a section to `.vscode/launch.json` similar to the one provided and launch it.

