FROM ubuntu:20.04
LABEL maintainer="engines-support@switch.ch"

ARG DEV_CONTAINER="false"

##################
#  stuff needed for Visual Code Dev Container ...
RUN if [ "$DEV_CONTAINER" = "true" ]; then \
    apt-get -y update && DEBIAN_FRONTEND=noninteractive apt-get -y install \
      iproute2 \
      tcpdump \
      python3-pip \
      procps \
      net-tools \
      pylint \
      flake8 \
      python3-autopep8 \
      yapf3 \
      black \
      mypy \
      pydocstyle \
      python3-bandit \
      pipenv \
      virtualenv \
    ; fi \
    && apt-get clean -y && rm -rf /var/lib/apt/lists/*

RUN  apt-get -y update && DEBIAN_FRONTEND=noninteractive apt-get -y install \
      python3-openstacksdk \
      python3-prometheus-client \
      python3-schedule \
      curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir /opt/openstack-exporter
COPY openstack-exporter /opt/openstack-exporter
RUN chmod +x /opt/openstack-exporter/openstack-exporter.py

EXPOSE 9103

CMD ["/opt/openstack-exporter/openstack-exporter.py"]


