###################################################################
# Base container
FROM python:3.10 AS base

ARG DEBIAN_FRONTEND=noninteractive

RUN apt update && apt -y upgrade

# we'll end up blowing away this directory via docker-compose
WORKDIR /service
COPY pyproject.toml .
COPY poetry.lock .
RUN pip install 'poetry==1.2.2'
RUN poetry config virtualenvs.create false && poetry install

RUN mkdir /images

EXPOSE 80/tcp

ENV FLASK_APP=files/cli:app


###################################################################
# Release container
FROM base AS release

COPY bootstrap/supervisord.conf.release /etc/supervisord.conf
CMD [ "/usr/local/bin/supervisord", "-c", "/etc/supervisord.conf" ]


###################################################################
# Dev container
FROM release AS dev

# Install our tweaked sqlalchemy-easy-profile
COPY thirdparty/sqlalchemy-easy-profile sqlalchemy-easy-profile
RUN cd sqlalchemy-easy-profile && python3 setup.py install

COPY bootstrap/supervisord.conf.dev /etc/supervisord.conf
CMD [ "/usr/local/bin/supervisord", "-c", "/etc/supervisord.conf" ]


###################################################################
# Utility container for running commands (tests, most notably)
FROM release AS operation

# don't run the server itself, just start up the environment and assume we'll exec things from the outside
CMD sleep infinity

# Turn off the rate limiter
ENV DBG_LIMITER_DISABLED=true
