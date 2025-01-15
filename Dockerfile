FROM python:3.13

ARG POETRY_VERSION=1.0

ENV TELEGRAM_DAEMON_DEST="/downloads"
ENV TELEGRAM_DAEMON_SESSION_PATH="/session"
ENV TELEGRAM_DAEMON_TEMP="/temp"

WORKDIR /usr/src/telegram-download-daemon-ng

COPY . /usr/src/telegram-download-daemon-ng

RUN python3 -m pip install "poetry~=${POETRY_VERSION}"
RUN python3 -m poetry install --no-interaction

CMD [ "poetry", "run", "python3", "-m", "telegram_download_daemon_ng" ]
