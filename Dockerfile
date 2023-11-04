FROM python:3.12

WORKDIR /app

COPY . /app

RUN python3 -m pip install /app

CMD [ "python3", "/app/src/telegram-download-daemon.py" ]
