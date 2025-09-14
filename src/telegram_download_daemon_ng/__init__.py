import asyncio
import logging
import multiprocessing
import os
import re
import subprocess
import traceback
from mimetypes import guess_extension

from telethon import TelegramClient, events, __version__ as telethon_version
from telethon.tl.types import PeerChannel, DocumentAttributeFilename, DocumentAttributeVideo

from .download_media import DownloadMedia
from .session_manager import get_session, save_session
from . import config, constants, utils

logging.basicConfig(format='[%(levelname) 5s/%(asctime)s]%(name)s:%(message)s',
                    level=logging.WARNING)


class TelegramDownloadDaemon:
    def __init__(self, args):
        self.api_id = args.api_id
        self.api_hash = args.api_hash
        self.channel_id = args.channel
        self.bot = args.bot

        self.worker_count = multiprocessing.cpu_count()
        self.in_progress = {}

        config.download_folder = args.dest
        config.temp_folder = args.temp or args.dest
        config.duplicates = args.duplicates

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
                            await utils.log_reply(event, output, edit=True)
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
                            re.finditer(r"https://t.me/(c/)?(?P<message_channel>\w+)(/(?P<message_id>[0-9]+))?", event.message.message))

                        count_downloads = 0
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
                                                         destination=channel_msg.chat.title)
                                    count_downloads += 1
                            else:
                                await queue_download(event, channel=message_channel, message_id=message_id)
                                count_downloads += 1

                            return f"{command}\n{count_downloads} item(s) added to queue"
                        else:
                            return "Send message link to download or use available commands: list, status, clean."

            def list_download_folder():
                """
                Reply with the files and folders on downloads folder
                :return:
                TODO: Replace with python method instead of `ls`, to make compatible with Windows
                """
                return subprocess.run(["ls -l " + config.download_folder], shell=True, stdout=subprocess.PIPE,
                                      stderr=subprocess.STDOUT).stdout.decode('utf-8')

            def print_status():
                try:
                    if queue.qsize() > 0:
                        downloads="\n".join([" - {0}".format(value) for (value) in self.in_progress.values()])
                        return f"Active downloads\n{downloads}\nPending downloads: {queue.qsize()}"
                    else:
                        return "No active downloads"
                except:
                    return "Some error occurred while checking the status. Retry."

            def clean_downloads_folder():
                return "Cleaning {folder}\n{cmdOutput}".format(folder=config.temp_folder, cmdOutput=subprocess.run(
                    ["rm " + config.temp_folder + "/*." + constants.TELEGRAM_DAEMON_TEMP_SUFFIX], shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT).stdout)

            async def queue_download(event_message, channel, message_id, destination='.'):
                new_download_media = DownloadMedia(client=client, event_message=event_message, channel=channel, message_id=message_id, destination=destination)

                await queue.put(dict(download_media=new_download_media))

            async def worker():
                while True:
                    try:
                        item = await queue.get()
                        download_item: DownloadMedia = item['download_media']

                        if await utils.check_is_media_message(download_item):
                            self.in_progress[download_item.get_link()] = utils.get_filename(await download_item.get_message())
                            await download_item.download()
                            del self.in_progress[download_item.get_link()]
                        else:
                            await utils.log_reply(download_item.event_message,
                                                  f"Message {download_item.get_link()} has no media to download.",
                                                  edit=False)
                        queue.task_done()
                    except Exception as e:
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
