FROM python:3.12

WORKDIR /app

COPY . /app

ENV TELEGRAM_DAEMON_DEST "/downloads"
ENV TELEGRAM_DAEMON_SESSION_PATH "/session"
ENV TELEGRAM_DAEMON_TEMP "/temp"

RUN python3 -m pip install /app

CMD [ "python3", "/app/src/telegram_download_daemon.py" ]
