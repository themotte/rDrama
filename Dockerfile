FROM ubuntu:20.04

RUN apt update && apt install -y python3.8 python3-pip

COPY requirements.txt /service/requirements.txt

WORKDIR /service

RUN pip3 install -r requirements.txt

EXPOSE 80/tcp

CMD sudo -E gunicorn files.__main__:app -k gevent -w 2 --reload -b 0.0.0.0:80 --max-requests 1000 --max-requests-jitter 500