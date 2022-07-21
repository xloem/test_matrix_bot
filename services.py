
import logging

logger = logging.getLogger(__name__)

from service_matrix import Matrix

##### The interactions with chat services are separated from bot behavior.
##### This lets one change what platform the bot operates on, or what library it uses,
#####  by only changing a small part of the code.
##### Separating things this way is important when writing software.

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
        self.add(Matrix(self, username, password, server))

    def on_member(self, service, room, event_id, sender, membership, raw=None):
        self.on_message(service, room, event_id, sender, f"{membership}", raw=raw)
    def on_other(self, service, room, event_id, sender, raw=None, reply=None):
        self.on_message(service, room, event_id, sender, repr(raw), raw=raw, reply=reply)
    def on_message(self, service, room, event_id, sender, message, raw=None, reply=None):
        pass

    def _on_error(self, **kwparams):
        import traceback
        exc_str = traceback.format_exc()
        logger.error(f'{kwparams}')
        for line in exc_str.split('\n'):
            logger.error(line)
        self.on_error(**kwparams, exception_string = exc_str)
    def _on_member(self, service, room, event_id, sender, membership, raw=None):
        try:
            self.log(service, room, sender, membership)
            self.on_member(self, service, room, event_id, sender, membership, raw=raw)
        except Exception as exception:
            self._on_error(service=service, room=room, id=event_id, sender=sender, type='member', raw=raw, reply=reply, exception=exception)
    def _on_other(self, service, room, event_id, sender, raw=None, reply=None):
        try:
            self.log(service, room, sender, repr(raw))
            self.on_other(service, room, event_id, sender, raw=raw, reply=reply)
        except Exception as exception:
            self._on_error(service=service, room=room, id=event_id, sender=sender, type='other', raw=raw, reply=reply, exception=exception)
    def _on_message(self, service, room, event_id, sender, message, raw=None, reply=None):
        try:
            self.log(service, room, sender, message)
            if sender != service.user_id:
                self.on_message(service, room, event_id, sender, message, raw=raw, reply=reply)
        except Exception as exception:
            self._on_error(service=service, room=room, id=event_id, sender=sender, message=message, type='message', raw=raw, reply=reply, exception=exception)

    def log(self, service, room, sender, text):
        log_lines = text.split('\n')
        padding = ' ' * len(sender)
        logger.info(f'{room} {sender}: {log_lines[0]}')
        for extra_line in log_lines[1:]:
            logger.info(f'{room} {padding}: {extra_line}')
