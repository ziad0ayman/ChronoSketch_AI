import subprocess
from pathlib import Path
from src.director.assembler import Assembler


def test_assembler_ffmpeg_available():
    result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
    assert result.returncode == 0


def test_assembler_no_audio():
    asm = Assembler()
    try:
        asm.assemble("nonexistent.mp3")
        assert False, "Expected FileNotFoundError"
    except FileNotFoundError:
        pass
