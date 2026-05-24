# ChronoSketch_AI — Automated Whiteboard Animation System

Turn any audio recording into a whiteboard-style animated video — complete with hand-drawn SVG illustrations and synchronized captions.

## How It Works

```
audio.mp3
  └─► [EAR: whisper] ──► word_timestamps.json
  └─► [BRAIN: groq/llama3.3] ──► scene_plan.json
  └─► [LIBRARY: all-MiniLM-L6-v2 + cosine sim] ──► svg_paths.json
  └─► [HAND: stroke-dasharray tracer] ──► frame_*.png
  └─► [DIRECTOR: ffmpeg] ──► output.mp4
```

The pipeline consists of 5 phases:

1. **Ear** — Transcribes audio into word-level timestamps using OpenAI Whisper
2. **Brain** — Uses Llama 3.3 (via Groq) to plan drawing scenes from the transcript
3. **Library** — Embeds scene keywords and retrieves matching SVG icons via semantic similarity
4. **Hand** — Animates SVGs using stroke-dasharray tracing, outputting PNG frames
5. **Director** — Assembles frames + audio into the final MP4 via FFmpeg

## Features

- **No generative image models** — uses 1,700+ pre-verified Lucide SVG icons
- **Chunked LLM processing** — 30s windows for bounded prompts and mid-video adaptation
- **Velocity-based tracing** — perfect sync between drawing speed and narration
- **Modular architecture** — 5 independent phases with JSON data contracts
- **Skip any phase** — CLI flags let you restart from any checkpoint

## Requirements

- Python 3.14+
- FFmpeg (installed and on PATH)
- Groq API key (set `GROQ_API_KEY` in `.env`)

## Installation

```bash
git clone https://github.com/ziad0ayman/ChronoSketch_AI.git
cd ChronoSketch_AI
pip install .
```

## Usage

```bash
chronosketch --input audio.mp3 --output output.mp4
```

Skip previously completed phases:
```bash
chronosketch --input audio.mp3 --skip-stt --skip-brain
```

## Project Structure

```
src/
├── main.py              # Orchestrator
├── ear/                 # Phase 1: Speech-to-text
├── brain/               # Phase 2: Scene planning
├── library/             # Phase 3: Asset retrieval
├── hand/                # Phase 4: SVG animation
├── director/            # Phase 5: Video assembly
└── shared/              # Models & logger
```

## License

MIT
