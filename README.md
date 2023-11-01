# telegram-download-daemon-ng

[![License: GPL v3](https://img.shields.io/badge/License-GPL%20v3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Test](https://github.com/Nyaran/telegram-download-daemon-ng/actions/workflows/test.yml/badge.svg)](https://github.com/Nyaran/telegram-download-daemon-ng/actions/workflows/test.yml)
[![codecov](https://codecov.io/gh/Nyaran/telegram-download-daemon-ng/branch/main/graph/badge.svg?token=JAAQ2DCW9D)](https://codecov.io/gh/Nyaran/telegram-download-daemon-ng)
![PyPI - Downloads](https://img.shields.io/pypi/dw/telegram-download-daemon-ng)

[![Ko-fi](https://img.shields.io/badge/Ko--fi-Nyaran-blue?logo=ko-fi)](https://ko-fi.com/nyaran)
[![Buy me a coffee](https://img.shields.io/badge/Buy%20me%20a%20coffee-Nyaran-blue?logo=buy-me-a-coffee)](https://www.buymeacoffee.com/nyaran)

A Telegram Daemon (not a bot) for file downloading
automation [for channels of which you have admin privileges](https://github.com/alfem/telegram-download-daemon/issues/48).

Based on the original work of [@alfem](https://github.com/alfem): https://github.com/alfem/telegram-download-daemon

If you have got an Internet connected computer or NAS and you want to automate file downloading from Telegram channels,
this daemon is for you.

Telegram bots are limited to 20Mb file size downloads. So I wrote this agent or daemon to allow bigger downloads
(limited to 2GB by Telegram APIs).

# Installation

You need Python3 (3.6 works fine, 3.5 will crash randomly).

Install dependencies by running this command:

```shell
pip install .
```

Obtain your own api id: https://core.telegram.org/api/obtaining_api_id

# Usage

You need to configure these values:

| Environment Variable           | Command Line argument | Description                                                                                                                                                                                                                                                                 | Default Value         |
|--------------------------------|:---------------------:|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------|
| `TELEGRAM_DAEMON_API_ID`       |      `--api-id`       | api_id from https://core.telegram.org/api/obtaining_api_id                                                                                                                                                                                                                  |                       |
| `TELEGRAM_DAEMON_API_HASH`     |     `--api-hash`      | api_hash from https://core.telegram.org/api/obtaining_api_id                                                                                                                                                                                                                |                       |
| `TELEGRAM_DAEMON_CHANNEL`      |      `--channel`      | Channel id to download from it (Please, check [Issue 45](https://github.com/alfem/telegram-download-daemon/issues/45), [Issue 48](https://github.com/alfem/telegram-download-daemon/issues/48) and [Issue 73](https://github.com/alfem/telegram-download-daemon/issues/73)) |                       |
| `TELEGRAM_DAEMON_SESSION_PATH` |                       | Path with session files                                                                                                                                                                                                                                                     |                       |
| `TELEGRAM_DAEMON_DEST`         |       `--dest`        | Destination path for downloaded files                                                                                                                                                                                                                                       | `/telegram-downloads` |
| `TELEGRAM_DAEMON_TEMP`         |       `--temp`        | Destination path for temporary (download in progress) files                                                                                                                                                                                                                 | use --dest            |
| `TELEGRAM_DAEMON_DUPLICATES`   |    `--duplicates`     | What to do with duplicated files: ignore, overwrite or rename them                                                                                                                                                                                                          | rename                |

You can define them as Environment Variables, or put them as a command line arguments, for example:

```shell
python3 telegram_download_daemon.py --api-id <your-id> --api-hash <your-hash> --channel <channel-number>
```

Finally, resend any file link to the channel to start the downloading. This daemon can manage many downloads
simultaneously.

You can also 'talk' to this daemon using your Telegram client:

* Say "list" and get a list of available files in the destination path.
* Say "status" to the daemon to check the current status.
* Say "clean" to remove stale (*.tdd) files from temporary directory.

# Docker

TODO
