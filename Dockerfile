FROM ubuntu:24.04 as base

USER root

COPY xhost /usr/bin

WORKDIR /wififorge

COPY . .

RUN apt-get update -y && apt-get upgrade --fix-missing -y --no-install-recommends
RUN apt install -y git
RUN apt install -y sudo
RUN apt install -y python3-pip
RUN git config --global --add safe.directory $PWD
RUN git config --global --add safe.directory $PWD/Framework/john
RUN git submodule init
RUN git submodule update

RUN git config --global --add safe.directory $PWD/Framework/mininet-wifi/hostapd

RUN python3 -m pip config set global.break-system-packages true

RUN apt install -y curl wget
RUN chmod +x ./Framework/dependencies.sh
RUN ./Framework/dependencies.sh 

RUN apt-get install -y --no-install-recommends \
     aircrack-ng \
     john \
     dsniff \
     mininet --allow-downgrades \
     iputils-ping

RUN ./Framework/mininet-wifi/util/install.sh -Wlnfv
RUN make -C Framework/mininet-wifi install

