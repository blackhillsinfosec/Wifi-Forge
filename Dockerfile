FROM ubuntu:24.04

USER root

COPY xhost /usr/bin

WORKDIR /wififorge

COPY . .
 RUN apt-get update -y && apt-get upgrade --fix-missing -y
 RUN apt install -y \
    git \
    sudo \
    iputils-ping \
    nano