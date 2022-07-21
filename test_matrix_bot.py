"""
A test bot using the Python Matrix Bot API

Test it out by adding it to a group chat and doing one of the following:
1. Say "Hi"
2. Say !echo this is a test!
3. Say !d6 to get a random size-sided die roll result
"""

##### Remember to separate the bot interactions from its behavior, so other chatting systems can be used.

from matrix_service import Services
import logging


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    services = Services()
    services.add_matrix('test_matrix_bot', 'test_matrix_bot', 'https://matrix.org')
    services.wait()
