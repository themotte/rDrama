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
RUN poetry config virtualenvs.create false

# Chat compilation
ENV NODE_VERSION=16.13.0
RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
ENV NVM_DIRECTORY=/root/.nvm
RUN . "$NVM_DIRECTORY/nvm.sh" && nvm install ${NODE_VERSION}
RUN . "$NVM_DIRECTORY/nvm.sh" && nvm use v${NODE_VERSION}
RUN . "$NVM_DIRECTORY/nvm.sh" && nvm alias default v${NODE_VERSION}
ENV PATH="/root/.nvm/versions/node/v${NODE_VERSION}/bin/:${PATH}"
RUN npm i -g yarn

RUN mkdir /images

EXPOSE 80/tcp

ENV FLASK_APP=files/cli:app

CMD [ "bootstrap/init.sh" ]


###################################################################
# Release container
FROM base AS release

RUN poetry install --without dev

COPY bootstrap/supervisord.conf.release /etc/supervisord.conf


###################################################################
# Dev container
FROM release AS dev

RUN poetry install --with dev

# Install our tweaked sqlalchemy-easy-profile
COPY thirdparty/sqlalchemy-easy-profile sqlalchemy-easy-profile
RUN cd sqlalchemy-easy-profile && python3 setup.py install

COPY bootstrap/supervisord.conf.dev /etc/supervisord.conf


###################################################################
# Utility container for running commands (tests, most notably)
FROM dev AS operation

# don't run the server itself, just start up the environment and assume we'll exec things from the outside
CMD sleep infinity

# Turn off the rate limiter
ENV DBG_LIMITER_DISABLED=true
