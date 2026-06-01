# ChronoSketch_AI — Project Map

## TECH_STACK

| Layer | Technology | Version |
|---|---|---|
| Runtime | Python | 3.14.4 |
| STT | openai-whisper | 20250625 (large-v3) |
| LLM Router | groq (llama3.3-70b) | 1.2.0 |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) | 5.5.0 |
| Animation | stroke-dasharray/offset (programmatic SVG tracing) | — |
| Composition | FFmpeg | 2026-04-30 |
| Video Assembly | moviepy | 2.2.1 |
| Asset Store | Lucide Icons (~1,711 SVG) | latest (git submodule) |
| Data Models | Pydantic | latest |
| Test | pytest | latest |

## SYSTEM_FLOW

```
audio.mp3
  └─► [EAR: whisper] ──► word_timestamps.json
  └─► [BRAIN: groq/llama3.3] ──► scene_elements.json (scenes with elements)
  └─► [LIBRARY: all-MiniLM-L6-v2 + cosine sim] ──► svg_paths.json
  └─► [HAND: stroke-dasharray tracer + compositing] ──► frame_*.png
  └─► [DIRECTOR: ffmpeg] ──► output.mp4
```

### Data Contracts

**Ear Output** (`WordTimestamp`):
```json
{"word": "mitosis", "start": 1.24, "end": 1.56}
```

**Brain Output** (`SceneElement`):
```json
{
  "element_id": 3,
  "scene_id": 2,
  "keyword": "cell division",
  "start_time": 12.3,
  "end_time": 14.1,
  "pos_x": 660.0,
  "pos_y": 540.0
}
```
Groups into scenes by `scene_id`. Each scene is a self-contained whiteboard with 1..6 elements.

**Library Output** (`AssetMatch`):
```json
{"event_id": 3, "svg_path": "assets/lucide/circle-slash.svg"}
```

**Hand Input** per scene: grouped `SceneElement[]` → composite frames with sequential element drawing.
- Each element draws at its precomputed `(pos_x, pos_y)` position.
- Completed elements accumulate on the whiteboard.
- Elements within a scene draw one at a time.
- Clear (blank) only happens between scenes.

## ARCHITECTURE

### Partitioning: Domain-Driven (5 domains matching 5 phases)

```
src/
├── main.py              # Orchestrator: calls phases sequentially, wires I/O
├── shared/              # Reused across ≥2 phases
│   ├── models.py        # Pydantic: WordTimestamp, SceneEvent, SceneElement, AssetMatch
│   └── logger.py        # Async queue logger (INFO/WARN/ERROR)
├── ear/                 # Phase 1
│   └── transcriber.py
├── brain/               # Phase 2
│   ├── orchestrator.py  # Chunked LLM loop → SceneElement list with positions
│   └── schemas.py       # LLM prompt templates + SceneRaw/SceneRawElement validators
├── library/             # Phase 3
│   ├── indexer.py       # Build keyword→filename index from Lucide filenames
│   └── retriever.py     # embed(query) → cosine sim → top-1 file path
├── hand/                # Phase 4
│   ├── layout.py        # Precomputed (x,y) layouts for 1..6 elements
│   ├── tracer.py        # animate_svg() — stateless stroke-dasharray animation
│   └── renderer.py      # Scene compositing: accumulate elements per scene, output PNG frames
└── director/            # Phase 5
    └── assembler.py     # ffmpeg subprocess: frames + audio → .mp4
```

### Key Design Decisions

1. **Chunked LLM processing** (30s windows) — keeps prompt size bounded, enables mid-video adaptation.
2. **Lucide as submodule** — deterministic SVGs, no API calls, zero hallucination risk.
3. **Scene-based compositing** — elements accumulate on the whiteboard within a scene; clear only between scenes. Each scene is a complete story/concept.
4. **Sequential element drawing** — elements draw one at a time (not all at once), each starts after the previous finishes.
5. **Precomputed positions** — 1..6 elements positioned via `layout.py`; LLM never handles coordinates.
6. **FFmpeg for final assembly** — battle-tested, GPU-accelerable, handles audio multiplex natively.

### Constraints

- **No generative image models.** Lucide SVGs are pre-verified local files.
- **No micro-files.** Each module ≤300 lines. If a module exceeds 300 lines, split by function, not by file.
- **No premature abstraction.** `shared/` is created only after ≥2 phases need the same code.

## ORPHANS & PENDING

| Item | Status | Action |
|---|---|---|
| Lucide SVG repo (1,711 icons) | COMPLETED | `src/library/assets/` populated |
| whisper model (large-v3) download | COMPLETED | Auto-downloaded on first `Transcriber` init |
| all-MiniLM-L6-v2 download | COMPLETED | Cached after first `Retriever` init |
| pyproject.toml with pinned deps | COMPLETED | All versions locked |
| `.env` with API keys | PENDING | User must set `GROQ_API_KEY` |
| Phase 1 (Ear) | COMPLETED | `transcriber.py` — whisper word-level timestamps |
| Phase 2 (Brain) | COMPLETED | `orchestrator.py` + `schemas.py` — LLM scene+element planning with layout assignment |
| Phase 3 (Library) | COMPLETED | `indexer.py` + `retriever.py` — Mini-RAG asset lookup |
| Phase 4 (Hand) | COMPLETED | `tracer.py` + `renderer.py` + `layout.py` — sequential compositing |
| Phase 5 (Director) | COMPLETED | `assembler.py` — FFmpeg multiplex |
| Integration test | COMPLETED | Full pipeline verified: audio → .mp4 |
| Unit tests (20) | COMPLETED | All passing |
| White background fix | COMPLETED | `renderer.py` — white `<rect>` in composite SVGs |
| Pillow compositing | COMPLETED | `renderer.py` — cairosvg → PIL white-background paste |
| LLM scene+element prompt | COMPLETED | `schemas.py` — prompt outputs scenes with up to 6 elements |
| Sequential element drawing | COMPLETED | `renderer.py` — elements draw one at a time within a scene |
| Precomputed layouts | COMPLETED | `layout.py` — positions for 1..6 elements (no LLM coordinate handling) |
| Clear between scenes | COMPLETED | `renderer.py` — blank frames at scene boundaries |
| Stateless tracer | COMPLETED | `tracer.py` — `animate_svg()` and `total_length()` functions, no in-place mutation |
| Unit tests (20) | COMPLETED | 20 tests pass across all phases |
| CI config | PENDING | Post-MVP; not in scope |
| GPU acceleration (CUDA) | PENDING | Post-MVP; CPU fallback first |
| Web UI / API server | PENDING | Explicitly out of scope |
| `SceneEvent` (old format) | DEPRECATED | Kept for backward compat; `schemas.py` still exports `SCENE_EVENT_ADAPTER` |

### Known animation limitations (sequential drawing partially mitigates #3)

1. **~~Non-`<path>` elements not animated~~** — **FIXED**. `tracer.py` handles `path`, `rect`, `circle`, `ellipse`, `line`, `polyline`, `polygon`.

2. **Progress never reaches 1.0** — `progress = i / n_frames`. Last frame has `progress < 1.0`, leaving ~2-4% of every stroke undrawn. *Mitigated by sequential compositing since drawing time per element is typically generous.*

3. **~~All paths animate simultaneously~~** — **FIXED by architecture change**. Sequential element drawing (one element at a time) eliminates simultaneous animation. Within a single SVG, individual paths still animate in parallel (minor cosmetic issue for multi-path icons).

4. **Single-frame elements (n_frames=1) render invisible** — `duration ≥ 0.1s` clamp → `n_frames = max(int(0.1*24), 1) = 2`. But if `n_frames = 1`, progress=0 → stroke fully hidden.
