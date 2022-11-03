FROM python:3.11

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

CMD [ "/usr/bin/supervisord", "-c", "/etc/supervisord.conf" ]
