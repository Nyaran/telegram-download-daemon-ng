import math
import os
import random
import string
import time
from mimetypes import guess_extension

from humanize import naturalsize
from telethon.tl.custom import Message
from telethon.tl.types import DocumentAttributeFilename, DocumentAttributeVideo

from . import constants, config, download_media


def get_random_id(length: int) -> str:
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


async def log_reply(message: Message, reply: str, edit=False) -> Message:
    """
    Log a reply message to the console and optionally edit the message in Telegram
    :param message: The original message object
    :param reply: The reply message
    :param edit: If True, edit the message instead of sending a new one
    :return:
    """
    print(reply)

    if edit:
        return await message.edit(reply)
    return await message.reply(reply)

async def set_progress(link, filename, message, received, total):
    percentage = math.trunc(received / total * 10000) / 100

    progress_message = f"{link}\n{filename}: {percentage}% ({naturalsize(received)} / {naturalsize(total)})"

    current_time = time.time()
    if (current_time - config.last_update) > constants.STATUS_UPDATE_INTERVAL:
        await log_reply(message, progress_message, edit=True)
        config.last_update = current_time

async def check_is_media_message(message_media):
    if isinstance(message_media, download_media.DownloadMedia):
        message = await message_media.get_message()
    else:
        message = message_media

    if message.media:
        return hasattr(message.media, 'document') or hasattr(message.media, 'photo')

    return False

def get_filename(message):
    media_file_name = "unknown"

    if hasattr(message.media, 'photo'):
        media_file_name = str(message.media.photo.id) + ".jpeg"
    elif hasattr(message.media, 'document'):
        for attribute in message.media.document.attributes:
            if isinstance(attribute, DocumentAttributeFilename):
                media_file_name = attribute.file_name
                break
            if isinstance(attribute, DocumentAttributeVideo):
                if message.message != '':
                    media_file_name = message.message.split(os.linesep)[0]
                else:
                    media_file_name = str(message.media.document.id)
                media_file_name += guess_extension(message.media.document.mime_type)

    media_file_name = "".join(c for c in media_file_name if c.isalnum() or c in "()._- ")

    return media_file_name

def get_file_size(message):
    if hasattr(message.media, 'photo'):
        return 0  # Photo size is not directly available?
    elif hasattr(message.media, 'document'):
        return message.media.document.size

    return 0