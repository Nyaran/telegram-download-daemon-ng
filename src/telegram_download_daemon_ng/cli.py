import argparse
import os
import sys

TELEGRAM_DAEMON_API_ID = os.getenv("TELEGRAM_DAEMON_API_ID")
TELEGRAM_DAEMON_API_HASH = os.getenv("TELEGRAM_DAEMON_API_HASH")
TELEGRAM_DAEMON_CHANNEL = os.getenv("TELEGRAM_DAEMON_CHANNEL")
TELEGRAM_DAEMON_BOT = os.getenv("TELEGRAM_DAEMON_BOT")

TELEGRAM_DAEMON_SESSION_PATH = os.getenv("TELEGRAM_DAEMON_SESSION_PATH")

TELEGRAM_DAEMON_DEST = os.getenv("TELEGRAM_DAEMON_DEST", "/telegram-downloads")
TELEGRAM_DAEMON_TEMP = os.getenv("TELEGRAM_DAEMON_TEMP", "")
TELEGRAM_DAEMON_DUPLICATES = os.getenv("TELEGRAM_DAEMON_DUPLICATES", "rename")

def cli():
    prog_name = os.path.basename(sys.argv[0])

    parser = argparse.ArgumentParser(
        prog="python3 -m " + __package__ if prog_name == "__main__.py" else prog_name,
        description="Script to download files from a Telegram Channel.")
    parser.add_argument(
        "--api-id",
        required=TELEGRAM_DAEMON_API_ID is None,
        type=int,
        default=TELEGRAM_DAEMON_API_ID,
        help='api_id from https://core.telegram.org/api/obtaining_api_id (default is TELEGRAM_DAEMON_API_ID env var)'
    )
    parser.add_argument(
        "--api-hash",
        required=TELEGRAM_DAEMON_API_HASH is None,
        type=str,
        default=TELEGRAM_DAEMON_API_HASH,
        help='api_hash from https://core.telegram.org/api/obtaining_api_id (default is TELEGRAM_DAEMON_API_HASH env var)'
    )
    parser.add_argument(
        "--dest",
        type=str,
        default=TELEGRAM_DAEMON_DEST,
        help='Destination path for downloaded files (default is /telegram-downloads).')
    parser.add_argument(
        "--temp",
        type=str,
        default=TELEGRAM_DAEMON_TEMP,
        help='Destination path for temporary files (default is using the same downloaded files directory).')
    parser.add_argument(
        "--bot",
        type=str,
        default=TELEGRAM_DAEMON_BOT,
        help='Bot identifier to use. If not present, it will be requested (or the phone number) on first start'
    )
    parser.add_argument(
        "--channel",
        required=TELEGRAM_DAEMON_CHANNEL is None,
        type=int,
        default=TELEGRAM_DAEMON_CHANNEL,
        help='Channel id to download from it (default is TELEGRAM_DAEMON_CHANNEL env var'
    )
    parser.add_argument(
        "--duplicates",
        choices=["ignore", "rename", "overwrite"],
        type=str,
        default=TELEGRAM_DAEMON_DUPLICATES,
        help='"ignore"=do not download duplicated files, "rename"=add a random suffix, "overwrite"=redownload and overwrite'
    )

    return parser
