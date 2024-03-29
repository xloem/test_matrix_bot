import os, psutil, queue, threading, types

import tqdm, torch
from prwkv.rwkvtokenizer import RWKVTokenizer
from prwkv.rwkvrnnmodel import RWKVRNN4NeoForCausalLM


import services

vm_snap, sw_snap = psutil.virtual_memory(), psutil.swap_memory()
if torch.cuda.is_available():
    # cuda: as much as cuda can hold if there is swap to transfer it
    MEMORY_BOUND = min(vm_snap.free + sw_snap.free, torch.cuda.mem_get_info()[0])
elif hasattr(vm_snap, 'buffers'):
    # linux/bsd: reuse buffers for other tasks if swap can hold the buffers
    MEMORY_BOUND = min(vm_snap.available - vm_snap.buffers + sw_snap.free, vm_snap.available)
else:
    # other: keep half of ram free, requiring as much swap as ram to use it
    MEMORY_BOUND = (vm_snap.available + min(sw_snap.free, vm_snap.available)) / 2
del vm_snap, sw_snap

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
        self.model.half('bf16')
        if torch.cuda.is_available():
            param_size = sum([w.nelement() * w.element_size() for w in self.model.model.parameters()])
            _pending = [(self.model.model.__dict__, 'w', self.model.model.w)]
            _params = []
            while len(_pending):
                d, k, w = _pending.pop()
                if type(w) is types.SimpleNamespace:
                    w = w.__dict__
                if type(w) is dict:
                    for key, val in w.items():
                        _pending.append((w, key, val))
                else:
                    _params.append((d, k, w))
                    param_size += w.nelement() * w.element_size()
            if param_size < MEMORY_BOUND:
                for d, k, w in _params:
                    d[k] = w.to('cuda')#.to(torch.bfloat16)
                #self.model.model.to(torch.bfloat16)
                self.model.model.to('cuda')
                self.model.model.RUN_DEVICE = 'cuda'
        try:
            self.metadata = self.model.load_context(self.state_path)
        except FileNotFoundError:
            self.model.clear_memory()
            if default_ctx:
                self.add(default_ctx)
                self.metadata = default_ctx
            else:
                self.metadata = None
        if self.model.init_state is not None:
            self.model.init_state = self.model.init_state.to(self.model.model.w.emb.weight.dtype).to(self.model.model.w.emb.weight.device)
        else:
            self.model.init_state = torch.zeros(self.model.model.args.n_layer * 5, self.model.model.args.n_embd, dtype=self.model.model.w.emb.weight.dtype, device=self.model.model.w.emb.weight.device)
    @property
    def state(self):
        return self.model.init_state
    def save(self, metadata = None):
        print(f'saving {self.state_path} ...')
        self.model.save_context(self.state_path, metadata or self.metadata)
        self.metadata = metadata or self.metadata
    def add(self, input_text, init_state = None, metadata = None):
        input_ids = self.tokenizer.encode(input_text).ids
        state = init_state or self.model.init_state
        for idx in range(len(input_ids) - 1):
           state = self.model.model.forward(input_ids[idx:idx+1], state, preprocess_only=True)
        self.model.init_logits, self.model.init_state = self.model.model.forward(input_ids[-1:], state)
        self.model.save_context(self.state_path, metadata or input_text)
        self.metadata = metadata or input_text
        return self
    def __enter__(self):
        return self
    def __exit__(self, exc_t, exc_v, exc_tb):
        self.save()
    def _ids_by_prob(self):
        logits, ids = self.model.init_logits.sort(descending=True)
        return ids
    def __iter__(self):
        while True:
            token_id = self.model.init_logits.argmax()
            self.model.init_logits, self.model.init_state = self.model.model.forward([token_id], self.model.init_state)
            yield self.tokenizer.decode((token_id,))

class RWKV(threading.Thread):
    def __init__(self, bot):
        super().__init__(daemon=True)
        self.bot = bot
        models = {
            'RWKV-4-14B': 14*10**9,
            'RWKV-4-3B': 3*10**9,
            'RWKV-4-1B5': 1.5*10**9,
            'RWKV-4-430M': 430*10**6,
            'RWKV-4-169M': 169*10**6,
        }
        for MODEL, param_count in models.items():
            if MEMORY_BOUND > param_count * 2:
                break
        self.rwkv = RWKVModel(MODEL, 'state--' + MODEL)
        if type(self.rwkv.metadata) is not dict:
            self.rwkv.metadata = {}
        self.incoming = queue.Queue()
        self.already_processed = set()
        self.start()
        for service in self.bot.services:
            for room in service.rooms.values():
                metadata = self.rwkv.metadata.get(room.name)
                history = room.history
                start_idx = 0
                for idx, event in enumerate(history):
                    if event.id == metadata:
                        start_idx = idx + 1
                for event in history[start_idx:]:
                    if event.id not in self.already_processed:
                        self.already_processed.add(event.id)
                        self.incoming.put(event)
    def on_message(self, msg):
        if msg.type != 'message':
            return
        if msg.sender == msg.service.user_id:
            if msg.id in self.already_processed:
                self.already_processed.remove(msg.id)
                return
        self.incoming.put(msg)
    def run(self):
        while True:
            msg = self.incoming.get()
            progress = tqdm.tqdm(self.incoming.qsize() + 1, leave=False)
            # the first item used to be separated out here,
            # so that the loop condition could be in the while statement.
            # doing that again would make it easier to use a context for the thinking emoji.
            progress.n = 0
            while True:
                progress.set_description(f'{msg.sender}: {msg.data}')
                self.rwkv.metadata[msg.room.name] = msg.id
                thinking_id = msg.service.react(msg, ':thinking_face:')
                self.rwkv.add(f'"{msg.sender}", in "{msg.room.name}", says: {msg.data}\n', metadata = self.rwkv.metadata)
                msg.service.confirm(msg)
                progress.n += 1
                if self.incoming.empty():
                    break
                else:
                    msg.service.delete(msg.room, thinking_id)
                progress.total = progress.n + self.incoming.qsize()
                msg = self.incoming.get()
            if msg.sender == msg.service.user_id or not msg.room.voice:
                progress.close()
                msg.service.delete(msg.room, thinking_id)
                continue
            progress.refresh()
            self.rwkv.add(f'"{msg.service.user_id}", in "{msg.room.name}", says:', metadata = self.rwkv.metadata)
            progress.close()
            progress = tqdm.tqdm(leave=False, total=128)
            progress.n = 0
            text = ''
            msg.service.typing(msg.room, True, 10000)
            for token in self.rwkv:
                msg.service.typing(msg.room, True, 10000)
                if not text:
                    token = token.lstrip()
                if token == '\n':
                    break
                assert '\n' not in token
                text += token
                if len(text) >= 256:
                    text += ' ...'
                    break
                progress.n += 1
                progress.set_description(text)
            progress.close()
            msg.service.delete(msg.room, thinking_id)
            send_id = msg.service.send(msg.room, text)
            msg.service.typing(msg.room, False)
            self.rwkv.metadata[msg.room.name] = send_id
            self.already_processed.add(send_id)
            self.rwkv.save(metadata=self.rwkv.metadata)

if __name__ == '__main__':
    #print('17: After the quick brown fox', end='', flush=True)
    with RWKVModel('RWKV-4-430M', 'RWKV-4-430M-rwkvstate', default_ctx = '17: After the qvick brown fox') as rwkv:
        for token in rwkv:
            print(token, end='', flush=True)
