import subprocess
from pathlib import Path
from src.shared.logger import logger
from src.shared.config import FPS


class Assembler:
    def __init__(self, frame_pattern: str = "data/frames/frame_%06d.png"):
        self._frame_pattern = frame_pattern

    def assemble(self, audio_path: str, output_path: str = "data/output/output.mp4") -> str:
        audio = Path(audio_path)
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        if not audio.exists():
            logger.error(f"Audio not found: {audio_path}")
            raise FileNotFoundError(f"Audio not found: {audio_path}")

        cmd = [
            "ffmpeg", "-y",
            "-framerate", str(FPS),
            "-i", self._frame_pattern,
            "-i", str(audio),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-shortest",
            str(output),
        ]
        logger.info(f"Assembling: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"FFmpeg failed: {result.stderr}")
            raise RuntimeError(f"FFmpeg failed: {result.stderr}")
        logger.info(f"Output: {output}")
        return str(output)
