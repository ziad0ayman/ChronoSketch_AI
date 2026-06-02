# ChronoSketch_AI — Automated Whiteboard Animation

Turn any audio recording into a whiteboard-style animated video with stroke-by-stroke SVG illustrations on a paper-textured background, synced to speech.

## Pipeline

```
audio.mp3
  └─► [EAR: whisper]        ──► words.json
  └─► [BRAIN: groq/llama]   ──► scenes.json
  └─► [LIBRARY: embeddings]  ──► assets.json (with candidates + scores)
  └─► [HAND: cairosvg + PIL] ──► frame_*.png (paper texture background)
  └─► [DIRECTOR: ffmpeg]     ──► output.mp4
```

## Requirements

- Python 3.14+
- FFmpeg (on PATH)
- Groq API key (set `GROQ_API_KEY` in `.env`)

## Install

```bash
pip install .
```

## Usage

```bash
# Full pipeline (interactive — prompts after each phase)
python -m src.main -i input.wav -o output.mp4

# Non-interactive (batch mode)
python -m src.main -i input.wav -o output.mp4 -y
```

### Per-phase review

After each phase the pipeline pauses and shows a summary. Press Enter to continue, or `q` to quit and edit the JSON file manually, then resume with `--skip-*` flags:

```bash
python -m src.main -i input.wav -o output.mp4 --skip-stt --skip-brain
```

| Flag | Skips | Loads from |
|---|---|---|
| `--skip-stt` | Transcription | `data/transcripts/words.json` |
| `--skip-brain` | LLM scene planning | `data/scenes/scenes.json` |
| `--skip-library` | SVG retrieval | `data/scenes/assets.json` |
| `--skip-render` | Frame rendering | `data/frames/` |

### Phase 3 — candidate scores

Assets display the top-5 semantic matches with cosine similarity so you can pick a different SVG:

```
  #3 'upload' -> upload-cloud.svg
         #1: upload-cloud    (score=0.924)
         #2: cloud-upload    (score=0.901)
         #3: share           (score=0.674)
         #4: hard-drive      (score=0.588)
         #5: download        (score=0.572)
```

Quit, edit `data/scenes/assets.json`, change `svg_path` to a different candidate, then resume with `--skip-library`.

### Debug phases

Standalone per-phase debug scripts produce detailed logs:

```bash
python debug_phase1.py   # word timestamps
python debug_phase2.py   # LLM scene plan
python debug_phase3.py   # SVG candidates with scores
python debug_phase4.py   # rendering timeline + tracer
```

## Architecture

```
src/
├── main.py               # Pipeline CLI with interactive checkpoints
├── ear/transcriber.py    # Phase 1: Whisper → word timestamps
├── brain/                # Phase 2: Groq LLM → scene+element plan
│   ├── orchestrator.py   #   Scene planning, word-aligned timing
│   └── schemas.py        #   Prompt builder + Pydantic models
├── library/              # Phase 3: Semantic SVG retrieval
│   ├── indexer.py        #   Build keyword index from filenames
│   └── retriever.py      #   all-MiniLM-L6-v2 + cosine similarity
├── hand/                 # Phase 4: SVG animation + frame compositing
│   ├── tracer.py         #   Stateless stroke-dasharray animation
│   ├── renderer.py       #   PIL-based multi-element compositing
│   └── layout.py         #   Precomputed positions for 1-6 elements
├── director/assembler.py # Phase 5: FFmpeg audio+frame assembly
└── shared/               # Data models, config, logger
    ├── models.py
    └── config.py
```

## License

MIT
