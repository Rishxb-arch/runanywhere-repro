import runanywhere as ra, inspect
from runanywhere import EmbedOptions, AudioInput, VadOptions, LlmOptions, ToolDefinition
ra.initialize()
v = ra.embeddings.embed(["hello world", "bonjour"], EmbedOptions(model="minilm"))
e=v[0]; print("embed ->", type(v), len(v), type(e), [x for x in dir(e) if not x.startswith("_")])
print("VadOptions fields:", inspect.signature(VadOptions))
for thr in (None, 0.5, 0.05, 0.01):
    o = VadOptions() if thr is None else VadOptions(activation_threshold=thr)
    try: print("vad", thr, ra.vad.detect(AudioInput.file("beckett.wav"), o))
    except Exception as e: print("vad", thr, "ERR", e)
schema = {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]}
calls=[]
ra.llm.tools.register(ToolDefinition(name="get_weather", parameters=schema, description="Current weather for a city"), lambda a: (calls.append(a), {"temp_c": 21})[1])
r = ra.llm.generate("What's the weather in Berlin right now? Use the get_weather tool.", LlmOptions(model="qwen2.5-0.5b", max_output_tokens=120))
print("qwen tools:", r.tool_calls, repr(r.text[:200]), "handler calls:", calls)
