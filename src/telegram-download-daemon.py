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

from download_media import DownloadMedia
from sessionManager import getSession, saveSession

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

parser = argparse.ArgumentParser(
    description="Script to download files from a Telegram Channel.")
parser.add_argument(
    "--api-id",
    required=TELEGRAM_DAEMON_API_ID == None,
    type=int,
    default=TELEGRAM_DAEMON_API_ID,
    help=
    'api_id from https://core.telegram.org/api/obtaining_api_id (default is TELEGRAM_DAEMON_API_ID env var)'
)
parser.add_argument(
    "--api-hash",
    required=TELEGRAM_DAEMON_API_HASH == None,
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
    required=TELEGRAM_DAEMON_CHANNEL == None,
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
updateFrequency = 10
lastUpdate = 0
# multiprocessing.Value('f', 0)

if not tempFolder:
    tempFolder = downloadFolder

# Edit these lines:
proxy = None


# End of interesting parameters

async def sendHelloMessage(client, peerChannel):
    entity = await client.get_entity(peerChannel)
    print("Telegram Download Daemon NG " + TDD_VERSION + " using Telethon " + __version__)
    await client.send_message(entity, "Telegram Download Daemon NG " + TDD_VERSION + " using Telethon " + __version__)
    await client.send_message(entity, "Hi! Ready for your files!")


async def log_reply(message, reply):
    print(reply)
    await message.edit(reply)


def getRandomId(len):
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choice(chars) for x in range(len))


def getFilename(event: events.NewMessage.Event):
    mediaFileName = "unknown"

    if hasattr(event.media, 'photo'):
        mediaFileName = str(event.media.photo.id) + ".jpeg"
    elif hasattr(event.media, 'document'):
        for attribute in event.media.document.attributes:
            if isinstance(attribute, DocumentAttributeFilename):
                mediaFileName = attribute.file_name
                break
            if isinstance(attribute, DocumentAttributeVideo):
                if event.message != '':
                    mediaFileName = event.message.split(os.linesep)[0]
                else:
                    mediaFileName = str(event.media.document.id)
                mediaFileName += guess_extension(event.media.document.mime_type)

    mediaFileName = "".join(c for c in mediaFileName if c.isalnum() or c in "()._- ")

    return mediaFileName


in_progress = {}


async def set_progress(filename, message, received, total):
    global lastUpdate
    global updateFrequency

    if received >= total:
        try:
            in_progress.pop(filename)
        except:
            pass
        return
    percentage = math.trunc(received / total * 10000) / 100

    progress_message = "{0} : {1}% ({2} / {3})".format(filename, percentage, naturalsize(received), naturalsize(total))
    in_progress[filename] = progress_message

    currentTime = time.time()
    if (currentTime - lastUpdate) > updateFrequency:
        await log_reply(message, progress_message)
        lastUpdate = currentTime


with TelegramClient(getSession(), api_id, api_hash,
                    proxy=proxy).start() as client:
    saveSession(client.session)

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
                    re.finditer(r"https://t.me/c/(?P<message_channel>[0-9]+)(/(?P<message_id>[0-9]+))?",
                                command))

                if download_uris:
                    for download_uri in download_uris:
                        message_channel = download_uri['message_channel']
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
                            await queue_download(event, DownloadMedia(channel=message_channel, message_id=message_id,
                                                                      destination='.'))

                else:
                    return "Send message link to download or use available commands: list, status, clean."


    def list_download_folder():
        """
        Reply with the files and folders on downloads folder
        :param event:
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
        reply_msg = await event.reply("{link} added to queue".format(link=download_media.get_link()))
        await queue.put(dict(event=event, download_media=download_media, reply_msg=reply_msg))


    async def get_media_message(message_media):
        if isinstance(message_media, DownloadMedia):
            message = await message_media.get_message(client)
        else:
            message = message_media

        if message.media:
            if hasattr(message.media, 'document') or hasattr(message.media, 'photo'):
                filename = getFilename(message)

                if (os.path.exists(os.path.join(tempFolder, "{0}.{1}".format(filename, TELEGRAM_DAEMON_TEMP_SUFFIX)))
                    or os.path.exists(os.path.join(downloadFolder, filename))) and duplicates == "ignore":
                    raise "{0} already exists. Ignoring it.".format(filename)

                return message
            else:
                raise "That is not downloadable. Try to send it as a file."


    async def worker():
        while True:
            try:
                item = await queue.get()
                download_media = item['download_media']
                reply_msg = item['reply_msg']

                message = await get_media_message(download_media)

                filename = getFilename(message)
                file_name, file_extension = os.path.splitext(filename)
                temp_filename = file_name + "-" + getRandomId(8) + file_extension

                temp_filepath = os.path.join(tempFolder, "{0}.{1}".format(temp_filename, TELEGRAM_DAEMON_TEMP_SUFFIX))
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
                set_progress(filename, reply_msg, 100, 100)

                if not os.path.exists(final_filepath_folder):
                    os.makedirs(final_filepath_folder)
                move(temp_filepath, final_filepath)
                await log_reply(reply_msg, "{0} ready".format(filename))

                queue.task_done()
            except Exception as e:
                try:
                    await log_reply(reply_msg, "Error: {}".format(str(e)))  # If it failed, inform the user about it.
                except:
                    pass
                print('Queue worker error: ', e)


    async def start():

        tasks = []
        loop = asyncio.get_event_loop()
        for i in range(worker_count):
            task = loop.create_task(worker())
            tasks.append(task)
        await sendHelloMessage(client, peerChannel)
        await client.run_until_disconnected()
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


    client.loop.run_until_complete(start())