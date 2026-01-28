# Use your base image
FROM mcr.microsoft.com/vscode/devcontainers/python:3.13

# Switch to vscode user
USER vscode
ENV HOME=/home/vscode

# Install elan
RUN curl https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh -sSf | sh -s -- -y
ENV PATH="$HOME/.elan/bin:$PATH"

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="$HOME/.local/bin:$PATH"