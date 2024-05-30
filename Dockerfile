FROM ubuntu:24.04

USER root

WORKDIR /wififorge

COPY . .
 RUN apt-get update -y && apt-get upgrade --fix-missing -y
 RUN apt install -y \
    git \
    sudo \
    iputils-ping \
    nano
#RUN ./Framework/setup.sh
#CMD service openvswitch-switch 