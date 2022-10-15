FROM ubuntu:22.04

ARG DEBIAN_FRONTEND=noninteractive

# python3-cachecontrol is currently required due to a dependency error in ubuntu 22.04's python3-poetry package
RUN apt update && apt -y upgrade && apt install -y supervisor python3-poetry ffmpeg python3-cachecontrol

COPY supervisord.conf /etc/supervisord.conf

# we'll end up blowing away this directory via docker-compose 
WORKDIR /service
COPY pyproject.toml .
COPY poetry.lock .
RUN poetry config virtualenvs.create false && poetry install

RUN mkdir /images && mkdir /songs

EXPOSE 80/tcp

CMD [ "/usr/bin/supervisord", "-c", "/etc/supervisord.conf" ]
