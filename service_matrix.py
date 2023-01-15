##### The interactions with chat services are separated from bot behavior.
##### This lets one change what platform the bot operates on, or what library it uses,
#####  by only changing a small part of the code.
##### Separating things this way is important when writing software.

# this code was modified from example_bot.py in the matrix_bot_api repository
# if rewritten, a more up-to-date library is https://github.com/poljar/matrix-nio .
# the matrix_bot_api code is not complex, so a rewrite ideally won't be either.

from matrix_bot_api.matrix_bot_api import MatrixBotAPI
from matrix_bot_api.mregex_handler import MRegexHandler
from matrix_bot_api.mcommand_handler import MCommandHandler

import services

class MatrixRoom(services.Room):
    def __init__(self, service, room):
        super().__init__(service, service._room2name(room), not room.guest_access, raw=room)
    @property
    def history(self):
        return [self.service._matrix2event(self.raw, event_raw) for event_raw in self.raw.events]
    @history.setter
    def history(self, ignored_content):
        pass

class Matrix(MatrixBotAPI):
    def __init__(self, handler, username, password, server):
        self.handler = handler
        # Create an instance of the MatrixBotAPI
        super().__init__(username, password, server)
        self.user_id = self.client.user_id
        self.rooms = {}
        self.rooms = {
            self._room2name(room): MatrixRoom(self, room)
            for room in self.client.get_rooms().values()
            if not room.guest_access
        }
        
    # read markers from https://github.com/matrix-org/matrix-python-sdk/pull/301
    def _send_read_markers(self, room_id, mfully_read, mread=None):
         """Perform PUT /rooms/$room_id/read_markers

         Args:
             room_id(str): The room ID.
             mfully_read (str): event_id the read marker should located at.
             mread (str): (optional) The event ID to set the read receipt location at.
         """

         content = {"m.fully_read": mfully_read}
         if mread:
             content['m.read'] = mread

         path = "/rooms/{}/read_markers".format(quote(room_id))
         return self.client.api._send("POST", path, content)

   
    @staticmethod
    def _room2name(room):
        if room.name is None:
            return room.room_id
        if ':' in room.name:
            return room.name
        else:
            return room.name + room.room_id[room.room_id.find(':'):]

    def send(self, room, message):
        result = room.raw.send_text(message)
        return result['event_id']
    
    def confirm(self, room, event):
        self._send_read_markers(room.room_id, event.id, event.id)

    def _matrix2event(self, room_raw, event_raw):
        event_id = event_raw['event_id']
        sender = event_raw['sender']
        room_name = self._room2name(room_raw)
        if room_name in self.rooms:
            room = self.rooms[room_name]
            room.raw = room_raw
        else:
            room = MatrixRoom(self, room_raw)
            self.rooms[room_name] = room
        if 'm.relates_to' in event_raw['content']:
            if 'm.in_reply_to' in event_raw['content']['m.relates_to']:
                reply_id = event_raw['content']['m.relates_to']['m.in_reply_to']['event_id']
            else:
                reply_id = event_raw['content']['m.relates_to']['event_id']
        else:
            reply_id = None
        data = None
        if event_raw['type'] == 'm.room.message':
            data = event_raw['content']['body']
            type = 'message'
        elif event_raw['type'] == 'm.room.member':
            data = event_raw['content']['membership']
            type = 'membership'
        elif event_raw['type'] == 'm.reaction':
            # note: emoji reactions are i think technically any message with m.relates_to.rel_type=m.annotation
            data = event_raw['content']['m.relates_to']['key']
            type = 'reaction'
        else:
            data = f"{event_raw['type']}: {repr(event_raw['content'])}"
            type = 'other'
        return services.Event(self, room, event_id, sender, type, data=data, raw=event_raw, reply=reply_id)

    def handle_message(self, room_raw, event_raw):
        event = self._matrix2event(room_raw, event_raw)
        self.handler._on_event(event)

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
            self.rooms[room_id] = MatrixRoom(self, room)
        else:
            print("Room not in allowed rooms list")
    
    def start(self):
        # Start polling
        super().start_polling()

    def wait(self):
        # Wait
        self.client.sync_thread.join()
        self.client.sync_thread = None

    def stop(self):
        #self.client.stop_listener_thread() # cannot join current thread
        self.client.should_listen = False
