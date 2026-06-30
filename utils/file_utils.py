from __future__ import annotations

import re
from pathlib import Path

def read_text_robust(path: Path) -> str:
    """Reads a text file trying UTF-8, UTF-8 with BOM, and CP1252/Latin-1.
    Also normalizes smart quotes to standard quotes to prevent parsing errors.
    """
    content = ""
    # Try UTF-8
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        # Try UTF-8 with BOM
        try:
            content = path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            # Fallback to cp1252
            content = path.read_text(encoding="cp1252")
            
    # Normalize smart quotes
    content = (
        content.replace("“", '"')
        .replace("”", '"')
        .replace("‘", "'")
        .replace("’", "'")
    )
    return content
