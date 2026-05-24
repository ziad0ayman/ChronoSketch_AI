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
| Asset Store | Lucide Icons (~1,500 SVG) | latest (git submodule) |
| Data Models | Pydantic | latest |
| Test | pytest | latest |

## SYSTEM_FLOW

```
audio.mp3
  └─► [EAR: whisper] ──► word_timestamps.json
  └─► [BRAIN: groq/llama3.3] ──► scene_plan.json (state-machine actions)
  └─► [LIBRARY: all-MiniLM-L6-v2 + cosine sim] ──► svg_paths.json
  └─► [HAND: stroke-dasharray tracer] ──► frame_*.png
  └─► [DIRECTOR: ffmpeg] ──► output.mp4
```

### Data Contracts

**Ear Output** (`WordTimestamp`):
```json
{"word": "mitosis", "start": 1.24, "end": 1.56}
```

**Brain Output** (`SceneEvent`):
```json
{
  "event_id": 3,
  "action": "draw",
  "start_time": 12.3,
  "end_time": 14.1,
  "search_keyword": "cell division diagram"
}
```
`action` ∈ {`draw`, `clear_canvas`}.

**Library Output** (`AssetMatch`):
```json
{"event_id": 3, "svg_path": "assets/lucide/circle-slash.svg"}
```

**Hand Input** per event: `svg_path` + `start_time` + `end_time` → draws SVG via stroke-dasharray animation over `n_frames = duration * FPS`.

## ARCHITECTURE

### Partitioning: Domain-Driven (5 domains matching 5 phases)

```
src/
├── main.py              # Orchestrator: calls phases sequentially, wires I/O
├── shared/              # Reused across ≥2 phases
│   ├── models.py        # Pydantic: WordTimestamp, SceneEvent, AssetMatch
│   └── logger.py        # Async queue logger (INFO/WARN/ERROR)
├── ear/                 # Phase 1
│   └── transcriber.py
├── brain/               # Phase 2
│   ├── orchestrator.py  # Chunked LLM loop
│   └── schemas.py       # LLM prompt templates + JSON validator
├── library/             # Phase 3
│   ├── indexer.py       # Build keyword→filename index from Lucide filenames
│   └── retriever.py     # embed(query) → cosine sim → top-1 file path
├── hand/                # Phase 4
│   ├── tracer.py        # svg.path→total_length, compute dash params per frame
│   └── renderer.py      # Cairo/HTML canvas: draw SVG, output PNG frames
└── director/            # Phase 5
    └── assembler.py     # ffmpeg subprocess: frames + audio → .mp4
```

### Key Design Decisions

1. **Chunked LLM processing** (30s windows) — keeps prompt size bounded, enables mid-video adaptation.
3. **Lucide as submodule** — deterministic SVGs, no API calls, zero hallucination risk.
4. **Velocity-based tracing** — `v = Σ(path_lengths) / (end_time - start_time)` ensures perfect sync.
5. **FFmpeg for final assembly** — battle-tested, GPU-accelerable, handles audio multiplex natively.

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
| Phase 2 (Brain) | COMPLETED | `orchestrator.py` + `schemas.py` — LLM scene planning |
| Phase 3 (Library) | COMPLETED | `indexer.py` + `retriever.py` — Mini-RAG asset lookup |
| Phase 4 (Hand) | COMPLETED | `tracer.py` + `renderer.py` — stroke-dasharray animation |
| Phase 5 (Director) | COMPLETED | `assembler.py` — FFmpeg multiplex |
| Integration test | COMPLETED | Full pipeline verified: audio → .mp4 |
| Unit tests (19) | COMPLETED | All passing across all phases |
| White background fix | COMPLETED | `tracer.py` — white `<rect>` inserted in all rendered SVGs |
| Duration padding fix | COMPLETED | `renderer.py` — persists last drawing during silence gaps, final padding to match `total_duration` |
| LLM timestamp grounding | COMPLETED | `schemas.py` — transcript now includes word-level `start-end` timestamps in prompt |
| Pillow white-bg compositing | COMPLETED | `renderer.py` — composites cairosvg output onto white `PIL.Image` for full-frame white background |
| LLM concept grouping | COMPLETED | `schemas.py` — prompt now demands GROUP EVERY WORD into 3-8 word scenes, min 2s, last event covers last word |
| Global event_id renumbering | COMPLETED | `orchestrator.py` — monotonically increasing IDs across chunks, preventing asset_map collision |
| Unit tests (21) | COMPLETED | All passing across all phases |
| CI config | PENDING | Post-MVP; not in scope |
| GPU acceleration (CUDA) | PENDING | Post-MVP; CPU fallback first |
| Web UI / API server | PENDING | Explicitly out of scope |
| Drawing animation inconsistency | INVESTIGATED | 3 root causes below |

### Animation issues (1 fixed, 3 remaining)

1. ~~**Non-`<path>` elements not animated** — `Tracer` only handled `<path>` elements. `<rect>`, `<line>`, `<circle>`, `<polygon>` rendered fully from frame 1 (e.g. `server.svg` popped in instantly).~~ **FIXED** — `tracer.py` now handles all strokeable SVG elements: `path`, `rect`, `circle`, `ellipse`, `line`, `polyline`, `polygon`.

2. **Progress never reaches 1.0** — `progress = i / n_frames` for `i ∈ [0, n_frames-1]`. Last frame has `progress = (n_frames-1)/n_frames < 1.0`. The final ~2-4% of every stroke is never drawn. Fix: change to `(i + 1) / n_frames`.

3. **All paths animate simultaneously** — Same `progress` applied to every element. Multi-element SVGs draw all strokes in parallel, not sequentially. Fix: sequential element animation with staggered progress.

4. **Single-frame events (n_frames=1) render invisible** — `duration ≥ 0.1s` clamp → `n_frames = max(int(0.1*24), 1) = 2`. But if `n_frames = 1`, progress=0 → stroke fully hidden.
