import os, queue, threading

from prwkv.rwkvtokenizer import RWKVTokenizer
from prwkv.rwkvrnnmodel import RWKVRNN4NeoForCausalLM

import services

class RWKVModel:
    def __init__(self, model_path, state_path, n_layer = None, n_embd = None, ctx_len = None, default_ctx = None):
        self.tokenizer = RWKVTokenizer.default()
        self.model = None
        if 'http' in model_path:
            fn = os.path.basename(model_patH)
            if not os.path.exists(fn):
                import urllib.request
                urllib.request.urlretrieve(model_path, fn)
            model_path = fn
        self.model_path = model_path
        self.state_path = state_path
        self.model = RWKVRNN4NeoForCausalLM.from_pretrained(model_path, n_layer, n_embd, ctx_len)
        try:
            self.model.load_context(self.state_path)
        except FileNotFoundError:
            self.model.clear_memory()
            if default_ctx:
                self.add(default_ctx)
    @property
    def state(self):
        return self.model.init_state
    def save(self):
        print(f'saving {self.state_path} ...')
        self.model.save_context(self.state_path)
    def add(self, input_text, init_state = None):
        input_ids = self.tokenizer.encode(input_text).ids
        state = init_state or self.model.init_state
        for idx in range(len(input_ids) - 1):
           state = self.model.model.forward(input_ids[idx:idx+1], state, preprocess_only=True)
        self.model.init_logits, self.model.init_state = self.model.model.forward(input_ids[-1:], state)
        self.model.save_context(self.state_path, input_text)
        return self
    def __enter__(self):
        return self
    def __exit__(self, exc_t, exc_v, exc_tb):
        self.save()
    def __iter__(self):
        while True:
            token_id = self.model.init_logits.argmax()
            self.model.init_logits, self.model.init_state = self.model.model.forward([token_id], self.model.init_state)
            yield self.tokenizer.decode([token_id])

class RWKV(threading.Thread):
    def __init__(self, bot):
        super().__init__(daemon=True)
        self.bot = bot
        self.rwkv = RWKVModel('RWKV-4-1B5', 'state--RWKV-4-1B5')
        self.incoming = queue.Queue()
        self.outgoing = set()
        self.start()
    def on_message(self, msg):
        if msg.sender == msg.service.user_id:
            note = (msg.room,msg.data)
            if note in self.outgoing:
                self.outgoing.remove(note)
                return
        self.incoming.put(msg)
    def run(self):
        while True:
            msg = self.incoming.get()
            services.logger.debug(f'processing {msg.sender} {msg.room}: {msg.data}')
            self.rwkv.add(f'{msg.sender} {msg.room}: {msg.data}\n')
            while not self.incoming.empty():
                msg = self.incoming.get()
                services.logger.debug(f'processing {msg.sender} {msg.room}: {msg.data}')
                self.rwkv.add(f'{msg.sender} {msg.room}: {msg.data}\n')
            if msg.sender == msg.service.user_id or msg.room not in msg.service.rooms:
                services.logger.debug(f'skipping send text, waiting for more messages')
                continue
            services.logger.debug(f'preparing to send text')
            self.rwkv.add(f'{msg.service.user_id} {msg.room}:')
            text = ''
            for token in self.rwkv:
                if not text:
                    token = token.lstrip()
                if token == '\n':
                    break
                assert '\n' not in token
                services.logger.debug(token)
                text += token
            note = (msg.room,text)
            self.outgoing.add(note)
            msg.service.send(msg.room, text)

if __name__ == '__main__':
    #print('17: After the quick brown fox', end='', flush=True)
    with RWKVModel('RWKV-4-1B5', 'RWKV-4-1B5-rwkvstate', default_ctx = '17: After the qvick brown fox') as rwkv:
        for token in rwkv:
            print(token, end='', flush=True)
