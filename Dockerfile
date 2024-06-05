FROM kalilinux/kali-rolling

USER root

COPY xhost /usr/bin

WORKDIR /wififorge

COPY . .

RUN apt-get update -y && apt-get upgrade --fix-missing -y --no-install-recommends
RUN apt install -y \
     git \
     sudo \
     python3-pip \
     curl \
     wget \
     mininet --allow-downgrades \
     john \
     wifiphisher \
     net-tools \
     dsniff \
     iputils-ping \
     wifite

RUN git config --global --add safe.directory $PWD
RUN git submodule init
RUN git submodule update

RUN git config --global --add safe.directory $PWD/Framework/mininet-wifi/hostapd

RUN python3 -m pip config set global.break-system-packages true
RUN wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
RUN apt-get install -y ./google-chrome-stable_current_amd64.deb

RUN ./Framework/mininet-wifi/util/install.sh -Wlnfv
RUN sudo make -C Framework/mininet-wifi install

