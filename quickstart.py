import time, runanywhere as ra
from runanywhere import LlmOptions
t0 = time.time(); ra.initialize(); print(f"init {time.time()-t0:.2f}s")
t0 = time.time()
r = ra.llm.generate("Explain quantum computing in one sentence.", LlmOptions(model="smollm2-360m"))
print(f"first generate (incl. download+load) {time.time()-t0:.1f}s")
print(repr(r.text))
print({k: getattr(r, k) for k in dir(r) if not k.startswith('_') and not callable(getattr(r, k))})
