"""Run every README snippet (bindings/python/README.md @ v0.20.37) and record what happens."""
import time, traceback, json, runanywhere as ra
from runanywhere import LlmOptions, ChatMessage, Role, ToolDefinition, AudioInput, SttOptions, TtsOptions, EmbedOptions, ModelRef, RagDocument
ra.initialize()
def step(name, fn):
    t0 = time.time()
    try: out = fn(); print(f"\n### {name} OK ({time.time()-t0:.1f}s)\n{out}", flush=True)
    except Exception as e: print(f"\n### {name} FAILED ({time.time()-t0:.1f}s): {type(e).__name__}: {e}", flush=True)
step("generate max_output_tokens=32 (model omitted)", lambda: (lambda r: (r.text, r.output_tokens, round(r.tokens_per_second,1), r.finish_reason))(ra.llm.generate("What is the capital of France?", LlmOptions(model="smollm2-360m", max_output_tokens=32))))
def stream():
    toks, res = [], None
    for ev in ra.llm.generate_stream("Describe a sunset."):
        if ev.is_token: toks.append(ev.text)
        elif ev.is_completed: res = ev.result
    return "".join(toks)[:300], res and (res.output_tokens, round(res.tokens_per_second,1))
step("generate_stream", stream)
step("multi-turn", lambda: ra.llm.generate([ChatMessage(Role.SYSTEM, "You are terse."), ChatMessage(Role.USER, "Who wrote Hamlet?")]).text)
schema = {"type": "object", "properties": {"city": {"type": "string"}, "temp_c": {"type": "integer"}}, "required": ["city", "temp_c"]}
step("generate_structured", lambda: (lambda r: (r.value, r.valid))(ra.llm.generate_structured("Weather in Paris, as JSON.", schema)))
calls = []
def tools():
    ra.llm.tools.register(ToolDefinition(name="get_weather", parameters=schema, description="Current weather"), lambda args: (calls.append(args), {"temp_c": 21})[1])
    r = ra.llm.generate("Weather in Berlin?"); return r.tool_calls, r.text[:300], "handler calls:", calls
step("tools", tools)
step("stt whisper-base (beckett.wav)", lambda: ra.stt.transcribe(AudioInput.file("beckett.wav"), SttOptions(model="whisper-base")))
step("tts piper-amy", lambda: (lambda a: (type(a).__name__, [x for x in dir(a) if not x.startswith('_')][:12]))(ra.tts.synthesize("Hello from RunAnywhere.", TtsOptions(voice="piper-amy"))))
step("vad", lambda: ra.vad.detect(AudioInput.file("beckett.wav")))
step("embed minilm", lambda: (lambda v: (getattr(v,'shape',None), getattr(v,'dtype',None)))(ra.embeddings.embed(["hello world"], EmbedOptions(model="minilm"))))
def rag():
    with ra.rag.open(ModelRef("minilm"), ModelRef("qwen2.5-0.5b")) as s:
        s.ingest(RagDocument("Paris is the capital of France.")); return s.search("capital of France?"), s.query("What is the capital of France?").answer
step("rag", rag)
