import os

from telethon.tl.types import PeerChannel


class DownloadMedia:

    def __init__(self, channel, message_id=None, destination='.'):
        self.channel = int(channel)
        self.message_id = int(message_id)
        self.destination = destination

    async def get_message(self, client):
        return await client.get_messages(PeerChannel(self.channel), 1, ids=self.message_id)

    def get_link(self):
        return os.path.join('https://t.me/c/', str(self.channel), str(self.message_id))
