FROM node:22-slim

# System packages: python3, ffmpeg, LaTeX (lualatex + xelatex), curl
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    curl \
    ffmpeg \
    ca-certificates \
    # LaTeX for CV and cover letter PDF generation
    texlive-luatex \
    texlive-xetex \
    texlive-latex-extra \
    texlive-fonts-extra \
    texlive-fonts-recommended \
    lmodern \
    fontconfig \
    # pdftotext for ATS verification
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Claude Code CLI + bun (required by telegram plugin server.ts)
RUN npm install -g @anthropic-ai/claude-code bun

# Python deps
RUN pip3 install --break-system-packages \
    requests \
    httpx \
    pydantic \
    python-dotenv \
    rapidfuzz \
    notion-client \
    feedparser \
    apscheduler

# Non-root user required by claude --dangerously-skip-permissions
RUN useradd -m -s /bin/bash hunter

# macOS-style home path so installed_plugins.json installPath resolves inside container
RUN mkdir -p /Users/vf && ln -sf /home/hunter/.claude /Users/vf/.claude

USER hunter
ENV HOME=/home/hunter

WORKDIR /app
COPY --chown=hunter:hunter . .

RUN chmod +x tools/channels/start.sh 2>/dev/null || true

ENV TELEGRAM_STATE_DIR=/home/hunter/.claude/channels/telegram-hunter-v2

ENTRYPOINT ["bash", "tools/channels/start.sh"]
