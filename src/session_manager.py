from os import getenv, path

from telethon.sessions import StringSession

TELEGRAM_DAEMON_SESSION_PATH = getenv("TELEGRAM_DAEMON_SESSION_PATH")
session_name = "DownloadDaemon"
string_session_filename = "{0}.session".format(session_name)


def _get_string_session_if_exists():
    session_path = path.join(TELEGRAM_DAEMON_SESSION_PATH,
                             string_session_filename)
    if path.isfile(session_path):
        with open(session_path, 'r') as file:
            session = file.read()
            print("Session loaded from {0}".format(session_path))
            return session
    return None


def get_session():
    if TELEGRAM_DAEMON_SESSION_PATH is None:
        return session_name

    return StringSession(_get_string_session_if_exists())


def save_session(session):
    if TELEGRAM_DAEMON_SESSION_PATH is not None:
        session_path = path.join(TELEGRAM_DAEMON_SESSION_PATH, string_session_filename)
        with open(session_path, 'w') as file:
            file.write(StringSession.save(session))
        print("Session saved in {0}".format(session_path))
