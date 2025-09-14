FROM python:3.13

ARG POETRY_VERSION=1.0

ENV TELEGRAM_DAEMON_DEST="/downloads"
ENV TELEGRAM_DAEMON_SESSION_PATH="/session"
ENV TELEGRAM_DAEMON_TEMP="/temp"

COPY dist/*.whl /tmp/dist/

RUN python3 -m pip install /tmp/dist/*.whl \
    && rm -rf /tmp/dist

CMD [ "python3", "-m", "telegram_download_daemon_ng" ]