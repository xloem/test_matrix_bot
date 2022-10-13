##### The interactions with chat services are separated from bot behavior.
##### This lets one change what platform the bot operates on, or what library it uses,
#####  by only changing a small part of the code.
##### Separating things this way is important when writing software.

# this code is from example_bot.py in the matrix_bot_api repository

from matrix_bot_api.matrix_bot_api import MatrixBotAPI
from matrix_bot_api.mregex_handler import MRegexHandler
from matrix_bot_api.mcommand_handler import MCommandHandler

import services

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

        data = None
        if event['type'] == 'm.room.message':
            data = event['content']['body']
            type = 'message'
        elif event['type'] == 'm.room.member':
            data = event['content']['membership']
            type = 'membership'
        else:
            data = f"{event['type']}: {repr(event['content'])}"
            type = 'other'
        self.handler._on_event(services.Event(self, room_name, event_id, sender, type, data=data, raw=raw, reply=reply_id))

    def handle_invite(self, room_id, state):
        # this overrides the base class invite handler to add rooms to a dict rather than a list.
        # i don't recall the original design plan well to know if this is the right solution.
        print("Got invite to room: " + str(room_id))
        if self.room_ids is None or room_id in self.room_ids:
            print("Joining...")
            room = self.client.join_room(room_id)
            # Add message callback for this room
            room.add_listener(self.handle_message)
            # Add room
            self.rooms[room_id] = room
        else:
            print("Room not in allowed rooms list")
    
    def start(self):
        # Start polling
        super().start_polling()

    def wait(self):
        # Wait
        self.client.sync_thread.join()

    def stop(self):
        raise NotImplementedError("stop can be implemented by looking in dependency library for what to call")
