#!/usr/bin/env python3
# Telegram Download Daemon NG
# Author: Luis Zurro <luiszurrodecos@gmail.com>
# Based on original work: Alfonso E.M. <alfonso@el-magnifico.org> [https://github.com/alfem/telegram-download-daemon]
# You need to install telethon (and cryptg to speed up downloads)

import argparse
import asyncio
import logging
import math
import multiprocessing
import os
import random
import re
import string
import subprocess
import time
import traceback
from mimetypes import guess_extension
from shutil import move

from humanize import naturalsize
from telethon import TelegramClient, events, __version__
from telethon.tl.types import PeerChannel, DocumentAttributeFilename, DocumentAttributeVideo

from .download_media import DownloadMedia
from .session_manager import get_session, save_session

logging.basicConfig(format='[%(levelname) 5s/%(asctime)s]%(name)s:%(message)s',
                    level=logging.WARNING)

TDD_VERSION = "0.0.1"

TELEGRAM_DAEMON_API_ID = os.getenv("TELEGRAM_DAEMON_API_ID")
TELEGRAM_DAEMON_API_HASH = os.getenv("TELEGRAM_DAEMON_API_HASH")
TELEGRAM_DAEMON_CHANNEL = os.getenv("TELEGRAM_DAEMON_CHANNEL")

TELEGRAM_DAEMON_SESSION_PATH = os.getenv("TELEGRAM_DAEMON_SESSION_PATH")

TELEGRAM_DAEMON_DEST = os.getenv("TELEGRAM_DAEMON_DEST", "/telegram-downloads")
TELEGRAM_DAEMON_TEMP = os.getenv("TELEGRAM_DAEMON_TEMP", "")
TELEGRAM_DAEMON_DUPLICATES = os.getenv("TELEGRAM_DAEMON_DUPLICATES", "rename")

TELEGRAM_DAEMON_TEMP_SUFFIX = "tdd"


def telegram_daemon_start():
    parser = argparse.ArgumentParser(
        description="Script to download files from a Telegram Channel.")
    parser.add_argument(
        "--api-id",
        required=TELEGRAM_DAEMON_API_ID is None,
        type=int,
        default=TELEGRAM_DAEMON_API_ID,
        help=
        'api_id from https://core.telegram.org/api/obtaining_api_id (default is TELEGRAM_DAEMON_API_ID env var)'
    )
    parser.add_argument(
        "--api-hash",
        required=TELEGRAM_DAEMON_API_HASH is None,
        type=str,
        default=TELEGRAM_DAEMON_API_HASH,
        help=
        'api_hash from https://core.telegram.org/api/obtaining_api_id (default is TELEGRAM_DAEMON_API_HASH env var)'
    )
    parser.add_argument(
        "--dest",
        type=str,
        default=TELEGRAM_DAEMON_DEST,
        help=
        'Destination path for downloaded files (default is /telegram-downloads).')
    parser.add_argument(
        "--temp",
        type=str,
        default=TELEGRAM_DAEMON_TEMP,
        help=
        'Destination path for temporary files (default is using the same downloaded files directory).')
    parser.add_argument(
        "--channel",
        required=TELEGRAM_DAEMON_CHANNEL is None,
        type=int,
        default=TELEGRAM_DAEMON_CHANNEL,
        help=
        'Channel id to download from it (default is TELEGRAM_DAEMON_CHANNEL env var'
    )
    parser.add_argument(
        "--duplicates",
        choices=["ignore", "rename", "overwrite"],
        type=str,
        default=TELEGRAM_DAEMON_DUPLICATES,
        help=
        '"ignore"=do not download duplicated files, "rename"=add a random suffix, "overwrite"=redownload and overwrite.'
    )
    args = parser.parse_args()

    api_id = args.api_id
    api_hash = args.api_hash
    channel_id = args.channel
    downloadFolder = args.dest
    tempFolder = args.temp
    duplicates = args.duplicates
    worker_count = multiprocessing.cpu_count()
    update_frequency = 10
    lastUpdate = 0
    # multiprocessing.Value('f', 0)

    if not tempFolder:
        tempFolder = downloadFolder

    # Edit these lines:
    proxy = None

    # End of interesting parameters

    async def send_hello_message(client_ref, peer_channel):
        entity = await client_ref.get_entity(peer_channel)
        message = "Telegram Download Daemon NG {} using Telethon {}".format(TDD_VERSION, __version__)
        print(message)
        await client_ref.send_message(entity, message)
        await client_ref.send_message(entity, "Hi! Ready for your files!")

    async def log_reply(message, reply):
        print(reply)
        await message.edit(reply)

    def get_random_id(length):
        chars = string.ascii_lowercase + string.digits
        return ''.join(random.choice(chars) for _ in range(length))

    def get_filename(event: events.NewMessage.Event):
        media_file_name = "unknown"

        if hasattr(event.media, 'photo'):
            media_file_name = str(event.media.photo.id) + ".jpeg"
        elif hasattr(event.media, 'document'):
            for attribute in event.media.document.attributes:
                if isinstance(attribute, DocumentAttributeFilename):
                    media_file_name = attribute.file_name
                    break
                if isinstance(attribute, DocumentAttributeVideo):
                    if event.message != '':
                        media_file_name = event.message.split(os.linesep)[0]
                    else:
                        media_file_name = str(event.media.document.id)
                    media_file_name += guess_extension(event.media.document.mime_type)

        media_file_name = "".join(c for c in media_file_name if c.isalnum() or c in "()._- ")

        return media_file_name

    in_progress = {}

    async def set_progress(filename, message, received, total):
        global lastUpdate
        global update_frequency

        if received >= total:
            try:
                in_progress.pop(filename)
            except:
                pass
            return
        percentage = math.trunc(received / total * 10000) / 100

        progress_message = "{0} : {1}% ({2} / {3})".format(filename, percentage, naturalsize(received),
                                                           naturalsize(total))
        in_progress[filename] = progress_message

        current_time = time.time()
        if (current_time - lastUpdate) > update_frequency:
            await log_reply(message, progress_message)
            lastUpdate = current_time

    with TelegramClient(get_session(), api_id, api_hash,
                        proxy=proxy).start() as client:
        save_session(client.session)

        queue = asyncio.Queue()
        peerChannel = PeerChannel(channel_id)

        @client.on(events.NewMessage())
        async def handler(event):
            if event.to_id != peerChannel:
                return

            print('Received: ', event)

            try:
                if (not event.media or hasattr(event.media, 'webpage')) and event.message:
                    output = await parse_command(event)

                    if output:
                        await log_reply(event, output)
                else:
                    # Message with attachment
                    if event.message.forward:
                        channel_msg = event.message.forward
                        await queue_download(event, DownloadMedia(channel=channel_msg.chat.id,
                                                                  message_id=channel_msg.channel_post,
                                                                  destination=os.path.join('.',
                                                                                           channel_msg.chat.title)))

                    else:
                        await queue_download(event, event.message)
            except Exception as e:
                print('Events handler error: ', e)
                traceback.print_tb(e.__traceback__)

        async def parse_command(event):
            command = event.message.message.lower()

            match command:
                case 'list':
                    return list_download_folder()
                case 'status':
                    return print_status()
                case 'clean':
                    return clean_downloads_folder()
                case _:  # default
                    download_uris = list(
                        re.finditer(r"https://t.me/(c/)?(?P<message_channel>\w+)(/(?P<message_id>[0-9]+))?",
                                    event.message.message))

                    if download_uris:
                        for download_uri in download_uris:
                            message_channel = download_uri['message_channel']
                            message_channel = message_channel if message_channel.isdigit() else (
                                await client.get_entity(message_channel)).id
                            message_id = download_uri['message_id']

                            if message_id is None:
                                channel_msgs = await client.get_messages(PeerChannel(int(message_channel)), None,
                                                                         reverse=True)

                                for channel_msg in channel_msgs:
                                    await queue_download(event, DownloadMedia(channel=channel_msg.chat.id,
                                                                              message_id=channel_msg.id,
                                                                              destination=os.path.join('.',
                                                                                                       channel_msg.chat.title)))
                            else:
                                await queue_download(event,
                                                     DownloadMedia(channel=message_channel, message_id=message_id,
                                                                   destination='.'))

                    else:
                        return "Send message link to download or use available commands: list, status, clean."

        def list_download_folder():
            """
            Reply with the files and folders on downloads folder
            :return:
            TODO: Replace with python method instead of `ls`, to make compatible with Windows
            """
            return subprocess.run(["ls -l " + downloadFolder], shell=True, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT).stdout.decode('utf-8')

        def print_status():
            try:
                if in_progress:
                    return "Active downloads\n{downloads}\nPending downloads: {pending}".format(
                        downloads="\n".join([" - {0}".format(value) for (value) in in_progress.values()]),
                        pending=queue.qsize())
                else:
                    return "No active downloads"
            except:
                return "Some error occurred while checking the status. Retry."

        def clean_downloads_folder():
            return "Cleaning {folder}\n{cmdOutput}".format(folder=tempFolder, cmdOutput=subprocess.run(
                ["rm " + tempFolder + "/*." + TELEGRAM_DAEMON_TEMP_SUFFIX], shell=True, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT).stdout)

        async def queue_download(event, download_media=None):
            item = download_media.get_link() if isinstance(download_media, DownloadMedia) else download_media.media
            reply_msg = await event.reply("{item} added to queue".format(item=item))
            await queue.put(dict(event=event, download_media=download_media, reply_msg=reply_msg))

        async def get_media_message(message_media):
            if isinstance(message_media, DownloadMedia):
                message = await message_media.get_message(client)
            else:
                message = message_media

            if message.media:
                if hasattr(message.media, 'document') or hasattr(message.media, 'photo'):
                    filename = get_filename(message)

                    if (os.path.exists(
                            os.path.join(tempFolder, "{0}.{1}".format(filename, TELEGRAM_DAEMON_TEMP_SUFFIX)))
                        or os.path.exists(os.path.join(downloadFolder, filename))) and duplicates == "ignore":
                        raise "{0} already exists. Ignoring it.".format(filename)

                    return message
                else:
                    raise "That is not downloadable. Try to send it as a file."

        async def worker():
            reply_msg = None
            while True:
                try:
                    item = await queue.get()
                    download_media = item['download_media']
                    reply_msg = item['reply_msg']

                    message = await get_media_message(download_media)

                    filename = get_filename(message)
                    file_name, file_extension = os.path.splitext(filename)
                    temp_filename = file_name + "-" + get_random_id(8) + file_extension

                    temp_filepath = os.path.join(tempFolder,
                                                 "{0}.{1}".format(temp_filename, TELEGRAM_DAEMON_TEMP_SUFFIX))
                    final_filepath_folder = os.path.join(downloadFolder, download_media.destination)
                    final_filepath = os.path.join(downloadFolder, download_media.destination, filename)

                    if (os.path.exists(temp_filepath) or os.path.exists(final_filepath)) and duplicates == "rename":
                        filename = temp_filename

                    if hasattr(message.media, 'photo'):
                        size = 0
                    else:
                        size = message.media.document.size

                    await log_reply(
                        reply_msg,
                        "Downloading file {0} ({1} bytes)".format(filename, size)
                    )

                    download_callback = lambda received, total: set_progress(filename, reply_msg, received, total)

                    await client.download_media(message, temp_filepath, progress_callback=download_callback)
                    await set_progress(filename, reply_msg, 100, 100)

                    if not os.path.exists(final_filepath_folder):
                        os.makedirs(final_filepath_folder)
                    move(temp_filepath, final_filepath)
                    await log_reply(reply_msg, "{0} ready".format(filename))

                    queue.task_done()
                except Exception as e:
                    try:
                        await log_reply(reply_msg,
                                        "Error: {}".format(str(e)))  # If it failed, inform the user about it.
                    except:
                        pass
                    print('Queue worker error: ', e)

        async def start():

            tasks = []
            loop = asyncio.get_event_loop()
            for i in range(worker_count):
                task = loop.create_task(worker())
                tasks.append(task)
            await send_hello_message(client, peerChannel)
            await client.run_until_disconnected()
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

        client.loop.run_until_complete(start())
