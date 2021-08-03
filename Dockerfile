FROM ubuntu:20.04

COPY supervisord.conf /etc/supervisord.conf

RUN apt update && apt install -y python3.8 python3-pip supervisor

RUN mkdir ./service

RUN pip3 install -r requirements.txt && cd ./service

EXPOSE 80/tcp

CMD [ "/usr/bin/supervisord", "-c", "/etc/supervisord.conf" ]
