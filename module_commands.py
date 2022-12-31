class Commands:
    def __init__(self, bot):
        self.bot = bot
        for service in self.bot.services:
            for room in service.rooms:
                service.send(room, "test_matrix_bot booting up")
    def __del__(self):
        for service in self.bot.services:
            for room in service.rooms.values():
                service.send(room, "test_matrix_bot shutting down")
    def on_message(self, msg):
        if msg.sender == msg.service.user_id:
            return
        if 'open%pdb' in msg.data:
            msg.service.send(msg.room, "I'm opening a PDB session to look at my code. You can look at this too, at https://github.com/xloem/test_matrix_bot . TODO: put commit hash here")
            import pdb
            try:
                pdb.set_trace()
            except pdb.bdb.BdbQuit:
                pass
            finally:
                msg.service.send(msg.room, "The PDB session has closed.")
        elif 'raise%exception' in msg.data:
            msg.service.send(msg.room, 'Are you sure? This is really scary ... Here we go; I\'ll raise an exception.')
            raise Exception(f"{msg.sender} asked me to raise this but I'm worried about it.")
        elif 'Hi' in msg.data:
            msg.service.send(msg.room, "Hi, " + msg.sender)
        elif msg.data.startswith('!echo'):
            msg.service.send(msg.room, msg.data[len('!echo')+1:])
        elif msg.data.startswith('!d'):
            room, event = msg.raw
            dieroll_callback(room, event)
        elif msg.data.startswith('!eval '):
            msg.service.send(msg.room, str(eval(msg.data[len('!eval '):], globals(), locals())))
        else:
            return False
        return True

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
