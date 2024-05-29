FROM ramonfontes/mininet-wifi:latest

WORKDIR /wififorge

COPY . .
RUN echo "PWD IS: $PWD"
RUN git config --global --add safe.directory $PWD
RUN git submodule init
RUN git submodule update


RUN apt-get update -y && apt-get upgrade -y
RUN apt-get install curl -y
#RUN chmod u+x Framework/dependencies.sh
#RUN ./Framework/dependencies.sh
#RUN apt update -y && apt upgrade -y
RUN apt install aircrack-ng -y
RUN apt install john -y
RUN apt install dsniff -y
RUN apt install mininet -y --allow-downgrades
RUN ./Framework/mininet-wifi/util/install.sh -Wlnfv
RUN apt install openvswitch-testcontroller -y
RUN ln /usr/bin/ovs-testcontroller /usr/bin/controller
#CMD python3 Framework/WifiForge.py
