FROM ubuntu:20.04

RUN apt update

RUN apt -y upgrade

RUN apt install -y supervisor

RUN apt install -y python3-pip

RUN apt install -y python3-enchant

RUN apt install -y libenchant1c2a

COPY supervisord.conf /etc/supervisord.conf

COPY requirements.txt /etc/requirements.txt

RUN pip3 install -r /etc/requirements.txt

RUN mkdir /images && mkdir /songs

EXPOSE 80/tcp

CMD [ "/usr/bin/supervisord", "-c", "/etc/supervisord.conf" ]