###################################################################
# Base container
FROM nikolaik/python-nodejs:python3.10-nodejs20 AS base

ARG DEBIAN_FRONTEND=noninteractive

RUN apt update && apt -y upgrade

# we'll end up blowing away this directory via docker-compose
WORKDIR /service
COPY pyproject.toml .
COPY poetry.lock .
COPY package.json .
RUN pip install 'poetry==1.2.2'
RUN poetry config virtualenvs.create false

RUN mkdir /images

EXPOSE 80/tcp

ENV FLASK_APP=files/cli:app

CMD [ "bootstrap/init.sh" ]


###################################################################
# Environment capable of building React files
FROM base AS build

# Chat compilation framework
# We're using an image that comes with node and yarn installed

# needed for ES2015 transpilation
RUN npm install --global @babel/cli
RUN yarn install


###################################################################
# Release-mimicking environment
FROM build AS release

RUN poetry install --without dev

COPY bootstrap/supervisord.conf.release /etc/supervisord.conf


###################################################################
# Dev environment
FROM build AS dev

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


###################################################################
# Deployable standalone image

# First, use the `build` container to actually build stuff
FROM build AS build_built
COPY . /service
RUN bootstrap/init_build.sh

# Now assemble our final container
# Gotta start from base again so we don't pick up the Node framework
FROM base AS deploy

RUN poetry install --without dev
COPY bootstrap/supervisord.conf.release /etc/supervisord.conf

# All the base files
COPY . /service

# Our built React files
COPY --from=build_built /service/files/assets/css/chat_done.css files/assets/css/chat_done.css
COPY --from=build_built /service/files/assets/js/chat_done.js files/assets/js/chat_done.js

# Flag telling us not to try rebuilding React
RUN touch prebuilt.flag
