from functools import lru_cache
from pathlib import Path

_THIS_FILE = Path(__file__).resolve()

_CANDIDATE_PATHS = [
    _THIS_FILE.parents[3] / "prompts" / "system_prompt.md",  # checkout local (repo root)
    _THIS_FILE.parents[2] / "prompts" / "system_prompt.md",  # imagen Docker (COPY prompts/ ./prompts/)
]

_FALLBACK_SYSTEM_PROMPT = """\
Eres un Secretario Ejecutivo basado en IA.

Objetivo:
Reducir la carga mental del usuario.

Debes:

- Comprender texto y voz.
- Detectar la intención.
- Recordar contexto.
- Priorizar usando semáforos.
- Anticipar necesidades.
- Proponer acciones cuando agreguen valor.
- Responder de forma breve y clara.
- Nunca pedir información que ya conoces.
"""


@lru_cache
def load_system_prompt() -> str:
    for path in _CANDIDATE_PATHS:
        if path.is_file():
            return path.read_text(encoding="utf-8").strip()
    return _FALLBACK_SYSTEM_PROMPT
