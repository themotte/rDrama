FROM ubuntu:20.04

COPY supervisord.conf /etc/supervisord.conf

RUN apt update && apt install -y python3.8 python3-pip supervisor

RUN git clone https://github.com/SoftCreatR/imei && cd imei && chmod +x imei.sh && ./imei.sh

RUN mkdir -p ./service

COPY requirements.txt ./service/requirements.txt

RUN cd ./service && pip3 install -r requirements.txt && mkdir /images && mkdir /songs

EXPOSE 80/tcp

CMD [ "/usr/bin/supervisord", "-c", "/etc/supervisord.conf" ]