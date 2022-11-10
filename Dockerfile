###################################################################
# Base/release container
FROM python:3.11 AS release

ARG DEBIAN_FRONTEND=noninteractive

RUN apt update && apt -y upgrade && apt install -y supervisor ffmpeg 

COPY supervisord.conf /etc/supervisord.conf

# we'll end up blowing away this directory via docker-compose 
WORKDIR /service
COPY pyproject.toml .
COPY poetry.lock .
RUN pip install 'poetry==1.2.2'
RUN poetry config virtualenvs.create false && poetry install

RUN mkdir /images && mkdir /songs

EXPOSE 80/tcp

ENV FLASK_APP=files/cli:app
CMD [ "/usr/bin/supervisord", "-c", "/etc/supervisord.conf" ]


###################################################################
# Dev container
FROM release AS dev
# we don't actually do anything different yet


###################################################################
# Utility container for running commands (tests, most notably)
FROM release AS operation

# don't run the server itself, just start up the environment and assume we'll exec things from the outside
CMD sleep infinity
