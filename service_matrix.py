##### The interactions with chat services are separated from bot behavior.
##### This lets one change what platform the bot operates on, or what library it uses,
#####  by only changing a small part of the code.
##### Separating things this way is important when writing software.

# this code is from example_bot.py in the matrix_bot_api repository

from matrix_bot_api.matrix_bot_api import MatrixBotAPI
from matrix_bot_api.mregex_handler import MRegexHandler
from matrix_bot_api.mcommand_handler import MCommandHandler

class Matrix(MatrixBotAPI):
    def __init__(self, handler, username, password, server):#username='test_matrix_bot', password='test_matrix_bot', server='https://matrix.org'):
        self.handler = handler
        # Create an instance of the MatrixBotAPI
        super().__init__(username, password, server)
        self.user_id = self.client.user_id
        self.rooms = {}

    def send(self, room_name, message):
        result = self.rooms[room_name].send_text(message)
        return result['event_id']

    def handle_message(self, room, event):
        event_id = event['event_id']
        sender = event['sender']
        raw = (room, event)
        room_name = room.name
        if room_name not in self.rooms:
            self.rooms[room_name] = room
        if 'm.relates_to' in event['content']:
            if 'm.in_reply_to' in event['content']['m.relates_to']:
                reply_id = event['content']['m.relates_to']['m.in_reply_to']['event_id']
            else:
                reply_id = event['content']['m.relates_to']['event_id']
        else:
            reply_id = None

        if event['type'] == 'm.room.message':
            message = event['content']['body']
            self.handler._on_message(self, room_name, event_id, sender, message, raw=raw, reply=reply_id)
        elif event['type'] == 'm.room.member':
            membership = event['content']['membership']
            self.handler._on_member(self, room_name, event_id, sender, membership, raw=raw)
        else:
            message = f"{event['type']}: {repr(event['content'])}"
            self.handler._on_other(self, room_name, event_id, sender, raw=raw, reply=reply_id)

    def start(self):
        # Start polling
        super().start_polling()

    def wait(self):
        # Wait
        self.client.sync_thread.join()

    def stop(self):
        raise NotImplementedError("stop can be implemented by looking in dependency library for what to call")
