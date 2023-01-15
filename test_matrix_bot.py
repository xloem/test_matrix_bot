"""
A test bot using the Python Matrix Bot API

Test it out by adding it to a group chat and doing one of the following:
1. Say "Hi"
2. Say !echo this is a test!
3. Say !d6 to get a random size-sided die roll result
"""

from services import Services
from module_commands import Commands
from module_rwkv import RWKV
import logging

class Bot(Services):
    def __init__(self, username='test_matrix_bot', password='test_matrix_bot', homeserver='https://matrix.org'):
        super().__init__()
        self.add_matrix(username, password, homeserver)
        self.modules = []
        self.modules.append(Commands(self))
        self.modules.append(RWKV(self))

    def __enter__(self):
        for module in self.modules:
            if hasattr(module, '__enter__'):
                module.__enter__()
        return self

    def __exit__(self, exc_t, exc_v, exc_tb):
        for module in self.modules:
            if hasattr(module, '__exit__'):
                module.__exit__(exc_t, exc_v, exc_tb)

    def on_error(self, event, exception, exception_string):
        for line in exception_string.split('\n'):
            event.service.send(event.room, line)

    def on_message(self, msg):
        for module in self.modules:
            if module.on_message(msg):
                break

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    with Bot() as bot:
        bot.wait()
