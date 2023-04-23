# telegram-download-daemon-ng

A Telegram Daemon (not a bot) for file downloading automation [for channels of which you have admin privileges](https://github.com/alfem/telegram-download-daemon/issues/48).

Based on the original work of [@alfem](https://github.com/alfem): https://github.com/alfem/telegram-download-daemon

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/E1E03K0RP)

If you have got an Internet connected computer or NAS and you want to automate file downloading from Telegram channels, this
daemon is for you.

Telegram bots are limited to 20Mb file size downloads. So I wrote this agent
or daemon to allow bigger downloads (limited to 2GB by Telegram APIs).

# Installation

You need Python3 (3.6 works fine, 3.5 will crash randomly).

Install dependencies by running this command:

    pip install -r requirements.txt

(If you don't want to install `cryptg` and its dependencies, you just need to install `telethon`)

Warning: If you get a `File size too large message`, check the version of Telethon library you are using. Old versions have got a 1.5Gb file size limit.


Obtain your own api id: https://core.telegram.org/api/obtaining_api_id

# Usage

You need to configure these values:

| Environment Variable     | Command Line argument | Description                                                  | Default Value       |
|--------------------------|:-----------------------:|--------------------------------------------------------------|---------------------|
| `TELEGRAM_DAEMON_API_ID`   | `--api-id`              | api_id from https://core.telegram.org/api/obtaining_api_id   |                     |
| `TELEGRAM_DAEMON_API_HASH` | `--api-hash`            | api_hash from https://core.telegram.org/api/obtaining_api_id |                     |
| `TELEGRAM_DAEMON_DEST`     | `--dest`                | Destination path for downloaded files                       | `/telegram-downloads` |
| `TELEGRAM_DAEMON_TEMP`     | `--temp`                | Destination path for temporary (download in progress) files                       | use --dest |
| `TELEGRAM_DAEMON_CHANNEL`  | `--channel`             | Channel id to download from it (Please, check [Issue 45](https://github.com/alfem/telegram-download-daemon/issues/45), [Issue 48](https://github.com/alfem/telegram-download-daemon/issues/48) and [Issue 73](https://github.com/alfem/telegram-download-daemon/issues/73))                              |                     |
| `TELEGRAM_DAEMON_DUPLICATES`  | `--duplicates`             | What to do with duplicated files: ignore, overwrite or rename them | rename                     |

You can define them as Environment Variables, or put them as a command line arguments, for example:

    python telegram-download-daemon.py --api-id <your-id> --api-hash <your-hash> --channel <channel-number>


Finally, resend any file link to the channel to start the downloading. This daemon can manage many downloads simultaneously.

You can also 'talk' to this daemon using your Telegram client:

* Say "list" and get a list of available files in the destination path.
* Say "status" to the daemon to check the current status.
* Say "clean" to remove stale (*.tdd) files from temporary directory.


# Docker

TODO

