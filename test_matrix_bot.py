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

import random

from matrix_bot_api.matrix_bot_api import MatrixBotAPI
from matrix_bot_api.mregex_handler import MRegexHandler
from matrix_bot_api.mcommand_handler import MCommandHandler

class ExampleBot(MatrixBotAPI):
    def __init__(self, username='test_matrix_bot', password='test_matrix_bot', server='https://matrix.org'):
        # Create an instance of the MatrixBotAPI
        super().__init__(username, password, server)

        ##### Remember to separate the bot interactions from its behavior, so other chatting systems can be plugged in.

        # Add a regex handler waiting for the word Hi
        hi_handler = MRegexHandler("Hi", self.hi_callback)
        self.add_handler(hi_handler)

        # Add a regex handler waiting for the echo command
        echo_handler = MCommandHandler("echo", self.echo_callback)
        self.add_handler(echo_handler)

        # Add a regex handler waiting for the die roll command
        dieroll_handler = MCommandHandler("d", self.dieroll_callback)
        self.add_handler(dieroll_handler)

    def handle_message(self, room, event):
        logger.info(f"{event['sender']}: {event['content']['body']}")
        super().handle_message(room, event)

    def start_polling(self):
        # Start polling
        super().start_polling()

        # Infinitely read stdin to stall main thread while the bot runs in other threads
        while True:
            input()

    def hi_callback(self, room, event):
        # Somebody said hi, let's say Hi back
        room.send_text("Hi, " + event['sender'])
    
    def echo_callback(self, room, event):
        args = event['content']['body'].split()
        args.pop(0)
    
        # Echo what they said back
        room.send_text(' '.join(args))
    
    def dieroll_callback(self, room, event):
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

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ExampleBot().start_polling()
