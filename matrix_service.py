"""
A test bot using the Python Matrix Bot API

Test it out by adding it to a group chat and doing one of the following:
1. Say "Hi"
2. Say !echo this is a test!
3. Say !d6 to get a random size-sided die roll result
"""

##### Remember to separate the bot interactions from its behavior, so other chatting systems can be used.

import logging

logger = logging.getLogger(__name__)

#import random

class Services:
    def __init__(self):
        self.services = []
    def wait(self):
        for service in self.services:
            service.wait()
    def add(self, service):
        self.services.append(service)
        service.start()
    def add_matrix(self, username, password, server):
        self.add(MatrixService(self, username, password, server))


    def on_other(self, service, room_name, event_id, sender, raw=None, reply=None):
        self.on_message(service, room_name, event_id, sender, repr(raw), raw=raw, reply=reply)

    def on_message(self, service, room_name, event_id, sender, message, raw=None, reply=None):
        try:
            log_lines = message.split('\n')
            padding = ' ' * len(sender)
            logger.info(f'{room_name} {sender}: {log_lines[0]}')
            for extra_line in log_lines[1:]:
                logger.info(f'{room_name} {padding}: {extra_line}')

            if sender == service.user_id:
                return
    
            if 'open%pdb' in message:
                service.send(room_name, "I'm opening a PDB session to look at my code. You can look at this too, at https://github.com/xloem/test_matrix_bot . TODO: put commit hash here")
                import pdb; pdb.set_trace()
                service.send(room_name, "The PDB session has closed.")
            elif 'raise%exception' in message:
                service.send(room_name, 'Are you sure? This is really scary ... Here we go; I\'ll raise an exception.')
                raise Exception(f"{sender} asked me to raise this but I'm worried about it.")
            elif 'Hi' in message:
                service.send(room_name, "Hi, " + sender)
            elif message.startswith('!echo'):
                service.send(room_name, message[len('!echo')+1:])
            elif message.startswith('!d'):
                room, event = raw
                dieroll_callback(room, event)
        except Exception as exception:
            import traceback
            exc_str = traceback.format_exc()
            logger.error(f'{repr(raw)}')
            for line in exc_str.split('\n'):
                logger.error(line)
                service.send(room_name, line)


from matrix_bot_api.matrix_bot_api import MatrixBotAPI
from matrix_bot_api.mregex_handler import MRegexHandler
from matrix_bot_api.mcommand_handler import MCommandHandler

class MatrixService(MatrixBotAPI):
    def __init__(self, handler, username, password, server):#username='test_matrix_bot', password='test_matrix_bot', server='https://matrix.org'):
        self.handler = handler
        # Create an instance of the MatrixBotAPI
        super().__init__(username, password, server)
        self.user_id = self.client.user_id
        self.rooms = {}

        ##### Remember to separate the bot interactions from its behavior, so other chatting systems can be plugged in.

    def send(self, room_name, message):
        self.rooms[room_name].send_text(message)

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
            self.handler.on_message(self, room_name, event_id, sender, message, raw=raw, reply=reply_id)
        else:
            message = f"{event['type']}: {repr(event['content'])}"
            self.handler.on_other(self, room_name, event_id, sender, raw=raw, reply=reply_id)

    def start(self):
        # Start polling
        super().start_polling()

    def wait(self):
        # Wait
        self.client.sync_thread.join()

    def stop(self):
        raise NotImplementedError("stop can be implemented by looking in dependency library for what to call")

    
def dieroll_callback(room, event):
    import random
    # someone wants a random number
    args = event['content']['body'].split()

    # we only care about the first arg, which has the die
    die = args[0]
    die_max = die[2:]

    # ensure the die is a positive integer
    if not die_max.isdigit():
        room.send_text('{} is not a positive number!'.format(die_max))
        return

    # and ensure it's a reasonable size, to prevent bot abuse
    die_max = int(die_max)
    if die_max <= 1 or die_max >= 1000:
        room.send_text('dice must be between 1 and 1000!')
        return

    # finally, send the result back
    result = random.randrange(1,die_max+1)
    room.send_text(str(result))
