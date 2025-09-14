import os
from pathlib import Path

from shutil import move

from telethon.tl.types import PeerChannel

from . import constants, utils, config


class DownloadMedia:

    def __init__(self, client, event_message, channel, message_id=None, destination='.', ):
        self.client = client
        self.event_message = event_message
        self.channel = int(channel)
        self.message_id = int(message_id)
        self.destination = destination
        self.reply_msg = None

    async def get_message(self):
        return await self.client.get_messages(PeerChannel(self.channel), 1, ids=self.message_id)

    def get_link(self):
        return os.path.join('https://t.me/c/', str(self.channel), str(self.message_id))

    def get_download_path(self, filename, as_temp=False):
        if as_temp:
            file = f"{filename}.{utils.get_random_id(8)}.{constants.TELEGRAM_DAEMON_TEMP_SUFFIX}"
            folder = config.temp_folder
        else:
            file = filename
            folder = os.path.join(config.download_folder, self.destination)

        return Path(os.path.join(folder, file))

    async def download(self):
        download_message = await self.get_message()
        filename = utils.get_filename(download_message)
        size = utils.get_file_size(download_message)
        download_link = self.get_link()

        reply_msg = await utils.log_reply(self.event_message,f"Starting download of {download_link} as {filename} ({size} bytes)", edit=False)

        # Prepare file paths
        temp_path = self.get_download_path(filename, as_temp=True)
        download_path = self.get_download_path(filename, as_temp=False)
        match config.duplicates:
            case "ignore":
                if os.path.exists(download_path):
                    print(f"{filename} already exists. Ignoring it.")
                    return
            case "rename":
                while os.path.exists(temp_path):
                    temp_path = temp_path.with_stem(f"{temp_path.stem}_{utils.get_random_id(4)}")

                while os.path.exists(download_path):
                    download_path = download_path.with_stem(f"{download_path.stem}_{utils.get_random_id(4)}")
                    filename = download_path.name
            case "overwrite":
                pass
            case _:
                raise ValueError("Invalid duplicates configuration")

        try:
            await utils.log_reply(reply_msg, f"Downloading {download_link} as {filename} ({size} bytes)", edit=True)

            download_callback = lambda received, total: utils.set_progress(download_link, filename, reply_msg, received, total)

            if not temp_path.parent.exists():
                os.makedirs(temp_path.parent)

            await self.client.download_media(download_message, temp_path, progress_callback=download_callback)
            await utils.set_progress(download_link, filename, reply_msg, 100, 100)

            if not download_path.parent.exists():
                os.makedirs(download_path.parent)

            move(temp_path, download_path)

            await utils.log_reply(reply_msg, f"{filename} ready", edit=True)
        except Exception as e:
            try:
                await utils.log_reply(reply_msg, f"Error: {str(e)}", edit=True)
            except:
                print('Download error: ', e)
