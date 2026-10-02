# RunAnywhere (Python SDK)

Notes from building the [RunAnywhere](https://github.com/RunanywhereAI/runanywhere-sdks) Python binding from source on
Linux and running every snippet in its README, with repros and a small tested patch for the build hints.

Once it is running, a lot of it works nicely, and it needs no account or key. Most of what I hit is packaging and docs.

> **Dates:** the install hints were re-run on 2 Oct 2026. The speech results (STT, TTS and VAD, items 4 and 5) come from runs on
> **26 Sep 2026** and were not re-run on 2 Oct.

## What I built

- Got the Python SDK running from source on Linux (the build takes 20+ minutes, about 1,200 ninja steps).
- `quickstart.py`: the README quick start, verbatim.
- `tour.py`: every README snippet (generate, stream, multi-turn, structured output, tools, STT, TTS, VAD, embeddings,
  RAG), with timings. Output in [`evidence/tour_stdout.txt`](evidence/tour_stdout.txt) and
  [`evidence/tour_stderr.txt`](evidence/tour_stderr.txt).
- `probe2.py`: follow-ups (VAD thresholds, the return type of `embed()`, tools with a larger model).

## Environment

| | |
|---|---|
| OS / hardware | Debian 13 x86_64, 8 vCPU shared VM (load 6-28 during the build, so timings are noisy), no GPU |
| Python | 3.12 (uv venv); g++, cmake, ninja from apt |
| Source | `RunanywhereAI/runanywhere-sdks` `main` @ `a18d1d3` (22 Sep 2026), package version 0.20.37 |
| README says | "Current release: 0.20.11" (`bindings/python/README.md`) |

## Verified issues

### 1. `pip install runanywhere==0.20.11` finds no package

```bash
./repro_install_hints.sh        # first section
```
```
error: No solution found when resolving dependencies
  cause: Because runanywhere was not found in the package registry and you require runanywhere==0.20.11, ...
PyPI JSON API status: 404
```
([`evidence/install_hints.txt`](evidence/install_hints.txt), re-run 2 Oct 2026.) PyPI returns 404 for `runanywhere`
(TestPyPI too), and none of the 67 assets in GitHub release `v0.20.37` is a `.whl`. `PACKAGING.md` describes the
PyPI / cibuildwheel flow, so this is probably "not published yet". No existing issue found (searched python / pypi).

### 2. Building from source: the error message's own install hint is unsatisfiable

Without the codegen tools, the build backend prints
([`evidence/build_missing_tools.txt`](evidence/build_missing_tools.txt)):

```
[runanywhere-build] cannot generate the IDL bindings; missing:
  protoc (see core/VERSIONS::PROTOC_VERSION)
  protobuf (pip install 'protobuf>=6.33,<7')
  grpcio-tools (pip install 'grpcio-tools==1.71.*')
```

but `grpcio-tools==1.71.*` requires `protobuf<6`, so following both lines fails
(second section of `repro_install_hints.sh`):

```
error: No solution found when resolving dependencies
  cause: Because grpcio-tools>=1.71.0rc2,<=1.71.2 depends on protobuf>=5.26.1,<6.0.dev0 and you require protobuf>=6.33,<7, ...
```

**What works:** install only `grpcio-tools==1.71.*` (which brings protobuf 5.29.6; the package's own `[test]` extra
allows `protobuf>=5.29`), then run `./idl/codegen/generate_all.sh --only python`.
Also: if `grpcio-tools` is missing, `generate_all.sh` prints "warning: grpcio-tools not installed; skipping" and still
ends with "complete".

**Fix:** `runanywhere-python-build-fixes.patch` makes the hint a single satisfiable line. Verified: with neither package
installed it prints one hint; after running that one command, only `protoc` is reported missing.

### 3. A plain source install cannot be imported: `libonnxruntime.so.1`

```
ImportError: libonnxruntime.so.1: cannot open shared object file: No such file or directory
```
(observed 26 Sep 2026; not captured in a log file.) The compiled `_core` has `NEEDED libonnxruntime.so.1` and
`RUNPATH $ORIGIN`, but a non-auditwheel build does not copy ONNX Runtime next to it. The copy CMake downloaded (1.28.0) lived
in a temporary build directory that was deleted after the build. `scripts/bundle_native.py` exists for this, but the README
doesn't mention it.

**Workaround:** copy a matching `libonnxruntime.so.1` into `runanywhere/_native/` (or build with `-C build-dir=build/py` and
run `python scripts/bundle_native.py build/py`). The README note in the patch documents this.

### 4. STT and TTS fail on the Linux source build, and the Python error hides the reason

```python
ra.stt.transcribe(AudioInput.file("beckett.wav"), SttOptions(model="whisper-base"))
ra.tts.synthesize("Hello from RunAnywhere.", TtsOptions(voice="piper-amy"))
```
```
### stt whisper-base (beckett.wav) FAILED (0.0s): SDKException: stt load_model
### tts piper-amy FAILED (20.3s): SDKException: tts load_voice
```
(`python tour.py`; the first STT call downloaded whisper-base, 72 s in my run, before failing. [`evidence/tour_stdout.txt`](evidence/tour_stdout.txt) was recorded with one extra STT step on a second clip; `tour.py` here has that step removed.)

The real cause appears only on stderr, at `initialize()` and on the first call
([`evidence/tour_stderr.txt`](evidence/tour_stderr.txt)):

```
[WARN] Sherpa: rac_plugin_register failed: -811 | file=rac_backend_sherpa_register.cpp:564
[ERROR] STT.Service: no registered plugin 'sherpa' serves transcribe | file=rac_service_factory_internal.h:299
```

(-811 is `RAC_ERROR_CAPABILITY_UNSUPPORTED`.) **Suggestions:** fail before downloading the model, and put the plugin reason in
the exception. No issue found; #693 describes a similar "plugin stops registering" regression for Swift.

### 5. VAD reports no speech on 10 s of clear speech, without raising

```python
ra.vad.detect(AudioInput.file("beckett.wav"))
```
```
VadResult(is_speech=False, probability=0.0, segments=[])
```

Same result with `VadOptions(activation_threshold=0.5 / 0.05 / 0.01)` (`python probe2.py`). The logs warn
`Energy threshold is very high (> 0.1) and may miss speech` even at the defaults. Likely the same missing sherpa/Silero
backend as issue 4, but here it fails silently. Related open issues: #896 / #897 (threshold handling).

### 6. The README tools snippet does not call the tool with the quick-start model

Following the README in order leaves `smollm2-360m` loaded. Then:

```python
ra.llm.generate("Weather in Berlin?")      # tools registered as in the README
```
```
([], "The weather in Berlin is quite varied. In the mornings, it can be chilly and rainy ...", 'handler calls:', [])
```

`tool_calls=[]`, the handler never runs, and the model invents a paragraph. With `LlmOptions(model="qwen2.5-0.5b")` it
works: `ToolCall(name='get_weather', arguments={'city': 'Berlin'}, result={'temp_c': 21})` and "The current temperature in
Berlin is 21 degrees Celsius." (`python probe2.py`). **Suggestion:** use a tool-capable model in the snippet, or warn when
the loaded model has no tool template.

### 7. Minor

- The README says `embed()` returns "numpy float32, L2-normalized"; it returns a `list[Embedding]` (`.index`, `.vector`).
- Every native log line is printed twice (`[RAC][WARN][X] ...` and `[WARN] X: ...`).
- `LLM service created successfully` is written to stdout without a newline, so it runs into the application's own output.
- Catalog models log `Model NOT found in registry (result=-423)` on every load.

## The patch

`runanywhere-python-build-fixes.patch` (against `main` @ `a18d1d3`; applies cleanly to that commit):

- `_build/ra_build_backend.py`: one satisfiable hint, `pip install 'grpcio-tools==1.71.*'  (also installs a compatible protobuf)` (issue 2)
- `bindings/python/README.md`: a short "Building from source (Linux)" note covering codegen, `-C build-dir=...` plus
  `scripts/bundle_native.py`, and the ONNX Runtime sidecar (issues 2 and 3)

## What worked well

- Once installed, `initialize()` takes 0.02 s, needs no account or key, and uses no network except model downloads.
- The quick start printed a sensible answer from `smollm2-360m` (download + load + generate 13.6 s; about 7-9 tok/s on this
  loaded VM, time to first token 0.8 s).
- `generate_structured` returned valid JSON matching the schema on the first try. RAG (`minilm` + `qwen2.5-0.5b`) ingested,
  searched (score 1.0) and answered correctly. Streaming and multi-turn were fine, and tools work with `qwen2.5-0.5b`.
- The build system is careful (clear prerequisite check, deterministic codegen, a sidecar bundler); the gaps are mostly docs
  and packaging.

## Files

| File | What it is |
|---|---|
| `quickstart.py` | README quick start |
| `tour.py` | every README snippet with timings (needs `beckett.wav` next to it) |
| `probe2.py` | VAD thresholds, `embed()` return type, tools with `qwen2.5-0.5b` |
| `repro_install_hints.sh` | issues 1 and 2 (needs `uv`) |
| `runanywhere-python-build-fixes.patch` | the patch described above |
| `beckett.wav` | 10 s test clip, copied from Moonshine's `test-assets/` (MIT) |
| `evidence/` | trimmed logs and outputs |
