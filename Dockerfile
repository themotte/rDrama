###################################################################
# Base container
FROM python:3.10 AS base

ARG DEBIAN_FRONTEND=noninteractive

RUN apt update && apt -y upgrade && apt install -y supervisor ffmpeg 

# we'll end up blowing away this directory via docker-compose
WORKDIR /service
COPY pyproject.toml .
COPY poetry.lock .
RUN pip install 'poetry==1.2.2'
RUN poetry config virtualenvs.create false && poetry install

RUN mkdir /images && mkdir /songs

EXPOSE 80/tcp

ENV FLASK_APP=files/cli:app


###################################################################
# Release container
FROM base AS release

COPY supervisord.conf.release /etc/supervisord.conf
CMD [ "/usr/bin/supervisord", "-c", "/etc/supervisord.conf" ]


###################################################################
# Dev container
FROM release AS dev

# Install our tweaked sqlalchemy-easy-profile
COPY thirdparty/sqlalchemy-easy-profile sqlalchemy-easy-profile
RUN cd sqlalchemy-easy-profile && python3 setup.py install

COPY supervisord.conf.dev /etc/supervisord.conf
CMD [ "/usr/bin/supervisord", "-c", "/etc/supervisord.conf" ]


###################################################################
# Utility container for running commands (tests, most notably)
FROM release AS operation

# don't run the server itself, just start up the environment and assume we'll exec things from the outside
CMD sleep infinity
