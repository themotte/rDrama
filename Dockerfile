FROM ubuntu:20.04

RUN apt update && apt -y upgrade && apt install -y python3.8 python3-pip supervisor python3-enchant

COPY supervisord.conf /etc/supervisord.conf

COPY requirements.txt /etc/requirements.txt

RUN pip3 install -r /etc/requirements.txt

RUN mkdir /images && mkdir /songs

EXPOSE 80/tcp

CMD [ "/usr/bin/supervisord", "-c", "/etc/supervisord.conf" ]