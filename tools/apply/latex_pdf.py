"""tools/apply/latex_pdf.py — Render cover letter to PDF via LaTeX.

Embeds a minimal article-class template and compiles it with lualatex
(or the binary named by the LATEX_ENGINE environment variable).
Runs the compiler twice for cross-reference stability.
"""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from pathlib import Path

LATEX_ENGINE = os.environ.get("LATEX_ENGINE", "lualatex")
OUTPUT_DIR = "cover_letters"

# Minimal LaTeX article template — cover letter text injected via placeholder
_TEMPLATE = r"""
\documentclass[12pt,a4paper]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{geometry}
\usepackage{parskip}
\geometry{margin=2.5cm}
\pagestyle{empty}

\begin{document}

%%COVER_LETTER_TEXT%%

\end{document}
""".strip()


def render_pdf(cover_letter_text: str, job_url: str) -> str:
    """Render cover letter text to a PDF file.

    Args:
        cover_letter_text: Plain-text cover letter (will be LaTeX-escaped).
        job_url:           Job posting URL (used to generate a unique filename).

    Returns:
        Absolute path to the generated ``.pdf`` file.

    Raises:
        RuntimeError: If the LaTeX compiler exits with a non-zero return code.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    safe_name = _url_to_filename(job_url)
    tex_path = os.path.join(OUTPUT_DIR, f"{safe_name}.tex")
    pdf_path = os.path.join(OUTPUT_DIR, f"{safe_name}.pdf")

    escaped = _latex_escape(cover_letter_text)
    tex_source = _TEMPLATE.replace("%%COVER_LETTER_TEXT%%", escaped)

    with open(tex_path, "w", encoding="utf-8") as fh:
        fh.write(tex_source)

    engine = os.environ.get("LATEX_ENGINE", LATEX_ENGINE)
    cmd = [engine, "--interaction=nonstopmode", "--output-directory", OUTPUT_DIR, tex_path]

    for _ in range(2):
        result = subprocess.run(
            cmd,
            capture_output=True,
        )
        if result.returncode != 0:
            stderr = result.stderr.decode(errors="replace") if result.stderr else ""
            raise RuntimeError(
                f"LaTeX compilation failed (exit {result.returncode}): {stderr[:500]}"
            )

    return os.path.abspath(pdf_path)


def _url_to_filename(url: str) -> str:
    """Convert a URL into a safe filename stem."""
    slug = re.sub(r"[^\w]", "_", url)
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug[:80] if slug else "cover_letter"


def _latex_escape(text: str) -> str:
    """Escape special LaTeX characters in plain text."""
    replacements = [
        ("\\", r"\textbackslash{}"),
        ("&", r"\&"),
        ("%", r"\%"),
        ("$", r"\$"),
        ("#", r"\#"),
        ("_", r"\_"),
        ("{", r"\{"),
        ("}", r"\}"),
        ("~", r"\textasciitilde{}"),
        ("^", r"\textasciicircum{}"),
    ]
    for char, escaped in replacements:
        text = text.replace(char, escaped)
    # Preserve paragraph breaks
    text = text.replace("\n\n", "\n\n\\medskip\n\n")
    return text
