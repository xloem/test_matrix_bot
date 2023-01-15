
import logging

logger = logging.getLogger(__name__)


##### The interactions with chat services are separated from bot behavior.
##### This lets one change what platform the bot operates on, or what library it uses,
#####  by only changing a small part of the code.
##### Separating things this way is important when writing software.

class Event:
    def __init__(self, service, room, id, sender, type, data=None, raw=None, reply=None):
        self.service = service
        self.room = room
        self.id = id
        self.sender = sender
        self.type = type
        self.data = data
        self.raw = raw
        self.reply = reply

class Room:
    def __init__(self, service, name, voice, members=[], history=[], raw=None):
        self.service = service
        self.name = name
        self.voice = voice
        self.members = members
        self.history = history
        self.raw = raw
    def send(self, message):
        return self.service.send(self, message)

class Services:
    def __init__(self):
        self.services = []
    def wait(self):
        for service in self.services:
            service.wait()
    def add(self, service):
        self.services.append(service)
        service.start()
    def stop(self):
        for service in self.services:
            service.stop()
    def add_matrix(self, username, password, server):
        import service_matrix
        self.add(service_matrix.Matrix(self, username, password, server))

    def on_member(self, event):
        self.on_message(event)
    def on_other(self, event):
        self.on_message(event)
    def on_message(self, event):
        logger.debug(f'{event.service} {event.room} {event.id} {event.sender} {event.type} {event.data} reply={event.reply}')
        pass

    def _on_error(self, event, exception):
        import traceback
        exc_str = traceback.format_exc()
        logger.error(f'{event.service} {event.room.name} {event.id} {event.sender} {event.type} {event.data} reply={event.reply}')
        for line in exc_str.split('\n'):
            logger.error(line)
        self.on_error(event, exception, exc_str)
    def _on_event(self, event):
        try:
            self.log(event.service, event.room, event.sender, event.data or '<no data>')
            if type == 'message':
                if event.sender != service.user_id:
                    self.on_message(event)
            elif type == 'membership':
                self.on_membership(event)
            else:
                self.on_other(event)
        except Exception as exception:
            self._on_error(event=event, exception=exception)

    def log(self, service, room, sender, text):
        log_lines = text.split('\n')
        padding = ' ' * len(sender)
        logger.info(f'{room.name} {sender}: {log_lines[0]}')
        for extra_line in log_lines[1:]:
            logger.info(f'{room.name} {padding}: {extra_line}')
