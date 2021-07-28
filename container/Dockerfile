FROM python:3.8.5-buster

## Install supporting packages
RUN apt-get update && apt-get install -y wget sox nano net-tools iputils-ping curl
RUN pip install -U pip
COPY requirements.txt .
RUN pip install -r requirements.txt

# Install NordVPN
ARG VERSION=3.7.4
RUN wget -O /tmp/nordrepo.deb https://repo.nordvpn.com/deb/nordvpn/debian/pool/main/nordvpn-release_1.0.0_all.deb && \
    apt install -y /tmp/nordrepo.deb && \
    apt update && \
    apt install -y nordvpn=$VERSION && \
    apt remove -y wget nordvpn-release

# Enable root user permissions
RUN apt-get update \
 && apt-get install -y sudo

RUN adduser --disabled-password --gecos '' docker
RUN adduser docker sudo
RUN echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

USER docker

WORKDIR /data/
CMD ["/usr/bin/sudo", "./start"]
