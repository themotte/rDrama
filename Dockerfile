FROM ubuntu:20.04

COPY supervisord.conf /etc/supervisord.conf

RUN apt update && apt install -y python3.8 python3-pip supervisor curl

COPY imei.sh /etc/imei.sh

RUN . /etc/imei.sh 

COPY requirements.txt /etc/requirements.txt

RUN pip3 install -r /etc/requirements.txt

RUN mkdir /images && mkdir /songs

EXPOSE 80/tcp

CMD [ "/usr/bin/supervisord", "-c", "/etc/supervisord.conf" ]