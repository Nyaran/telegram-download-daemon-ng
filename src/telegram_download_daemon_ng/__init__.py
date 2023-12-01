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
from telethon import TelegramClient, events, __version__ as telethon_version
from telethon.tl.types import PeerChannel, DocumentAttributeFilename, DocumentAttributeVideo

from .download_media import DownloadMedia
from .session_manager import get_session, save_session

logging.basicConfig(format='[%(levelname) 5s/%(asctime)s]%(name)s:%(message)s',
                    level=logging.WARNING)

TELEGRAM_DAEMON_TEMP_SUFFIX = "tdd"


class TelegramDownloadDaemon:
    def __init__(self, args):
        self.api_id = args.api_id
        self.api_hash = args.api_hash
        self.channel_id = args.channel
        self.bot = args.bot
        self.download_folder = args.dest
        self.temp_folder = args.temp
        self.duplicates = args.duplicates
        self.worker_count = multiprocessing.cpu_count()
        self.last_update = 0
        self.update_frequency = 10
        self.in_progress = {}

        if not self.temp_folder:
            self.temp_folder = self.download_folder

        # Edit these lines: TODO add parameter
        self.proxy = None

    @staticmethod
    async def send_hello_message(version, client_ref, peer_channel):
        entity = await client_ref.get_entity(peer_channel)
        message = "Telegram Download Daemon NG {} using Telethon {}".format(version, telethon_version)
        print(message)
        await client_ref.send_message(entity, message)
        await client_ref.send_message(entity, "Hi! Ready for your files!")

    @staticmethod
    async def log_reply(message, reply):
        print(reply)
        await message.edit(reply)

    @staticmethod
    def get_random_id(length):
        chars = string.ascii_lowercase + string.digits
        return ''.join(random.choice(chars) for _ in range(length))

    @staticmethod
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

    async def set_progress(self, filename, message, received, total):
        if received >= total:
            try:
                self.in_progress.pop(filename)
            except:
                pass
            return
        percentage = math.trunc(received / total * 10000) / 100

        progress_message = "{0} : {1}% ({2} / {3})".format(filename, percentage, naturalsize(received),
                                                           naturalsize(total))
        self.in_progress[filename] = progress_message

        current_time = time.time()
        if (current_time - self.last_update) > self.update_frequency:
            await self.log_reply(message, progress_message)
            self.last_update = current_time

    def start(self, version):
        with TelegramClient(get_session(), self.api_id, self.api_hash, proxy=self.proxy).start(
                bot_token=self.bot) as client:
            save_session(client.session)

            queue = asyncio.Queue()
            peer_channel = PeerChannel(self.channel_id)

            @client.on(events.NewMessage())
            async def handler(event):
                if event.to_id != peer_channel:
                    return

                print('Received: ', event)

                try:
                    if (not event.media or hasattr(event.media, 'webpage')) and event.message:
                        output = await parse_command(event)

                        if output:
                            await self.log_reply(event, output)
                    else:
                        # Message with attachment
                        if event.message.forward:
                            channel_msg = event.message.forward
                            await queue_download(event,
                                                 channel=channel_msg.chat.id,
                                                 message_id=channel_msg.channel_post,
                                                 destination=os.path.join('.', channel_msg.chat.title))

                        else:
                            await queue_download(event,
                                                 channel=event.message.peer_id.channel_id,
                                                 message_id=event.message.id)
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
                                        await queue_download(event,
                                                             channel=channel_msg.chat.id,
                                                             message_id=channel_msg.id,
                                                             destination=os.path.join('.', channel_msg.chat.title))
                                else:
                                    await queue_download(event, channel=message_channel, message_id=message_id)

                        else:
                            return "Send message link to download or use available commands: list, status, clean."

            def list_download_folder():
                """
                Reply with the files and folders on downloads folder
                :return:
                TODO: Replace with python method instead of `ls`, to make compatible with Windows
                """
                return subprocess.run(["ls -l " + self.download_folder], shell=True, stdout=subprocess.PIPE,
                                      stderr=subprocess.STDOUT).stdout.decode('utf-8')

            def print_status():
                try:
                    if self.in_progress:
                        return "Active downloads\n{downloads}\nPending downloads: {pending}".format(
                            downloads="\n".join([" - {0}".format(value) for (value) in self.in_progress.values()]),
                            pending=queue.qsize())
                    else:
                        return "No active downloads"
                except:
                    return "Some error occurred while checking the status. Retry."

            def clean_downloads_folder():
                return "Cleaning {folder}\n{cmdOutput}".format(folder=self.temp_folder, cmdOutput=subprocess.run(
                    ["rm " + self.temp_folder + "/*." + TELEGRAM_DAEMON_TEMP_SUFFIX], shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT).stdout)

            async def queue_download(event, channel, message_id, destination='.'):
                new_download_media = DownloadMedia(channel=channel, message_id=message_id, destination=destination)

                reply_msg = await event.reply("{item} added to queue".format(item=new_download_media.get_link()))
                await queue.put(dict(event=event, download_media=new_download_media, reply_msg=reply_msg))

            async def get_media_message(message_media):
                if isinstance(message_media, DownloadMedia):
                    message = await message_media.get_message(client)
                else:
                    message = message_media

                if message.media:
                    if hasattr(message.media, 'document') or hasattr(message.media, 'photo'):
                        filename = self.get_filename(message)

                        if (os.path.exists(
                                os.path.join(self.temp_folder, "{0}.{1}".format(filename, TELEGRAM_DAEMON_TEMP_SUFFIX)))
                            or os.path.exists(
                                    os.path.join(self.download_folder, filename))) and self.duplicates == "ignore":
                            raise "{0} already exists. Ignoring it.".format(filename)

                        return message
                    else:
                        raise "That is not downloadable. Try to send it as a file."

            async def worker():
                reply_msg = None
                while True:
                    try:
                        item = await queue.get()
                        download_item = item['download_media']
                        reply_msg = item['reply_msg']

                        message = await get_media_message(download_item)

                        filename = self.get_filename(message)
                        file_name, file_extension = os.path.splitext(filename)
                        temp_filename = file_name + "-" + self.get_random_id(8) + file_extension

                        temp_filepath = os.path.join(self.temp_folder,
                                                     "{0}.{1}".format(temp_filename, TELEGRAM_DAEMON_TEMP_SUFFIX))
                        final_filepath_folder = os.path.join(self.download_folder, download_item.destination)
                        final_filepath = os.path.join(final_filepath_folder, filename)

                        if (os.path.exists(temp_filepath) or os.path.exists(
                                final_filepath)) and self.duplicates == "rename":
                            filename = temp_filename

                        if hasattr(message.media, 'photo'):
                            size = 0
                        else:
                            size = message.media.document.size

                        await self.log_reply(
                            reply_msg,
                            "Downloading file {0} ({1} bytes)".format(filename, size)
                        )

                        download_callback = lambda received, total: self.set_progress(filename, reply_msg, received,
                                                                                      total)

                        await client.download_media(message, temp_filepath, progress_callback=download_callback)
                        await self.set_progress(filename, reply_msg, 100, 100)

                        if not os.path.exists(final_filepath_folder):
                            os.makedirs(final_filepath_folder)
                        move(temp_filepath, final_filepath)
                        await self.log_reply(reply_msg, "{0} ready".format(filename))

                        queue.task_done()
                    except Exception as e:
                        try:
                            await self.log_reply(reply_msg, "Error: {}".format(str(e)))
                        except:
                            pass
                        print('Queue worker error: ', e)

            async def start():
                tasks = []
                loop = asyncio.get_event_loop()
                for i in range(self.worker_count):
                    task = loop.create_task(worker())
                    tasks.append(task)
                await self.send_hello_message(version, client, peer_channel)
                await client.run_until_disconnected()
                for task in tasks:
                    task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)

            client.loop.run_until_complete(start())
