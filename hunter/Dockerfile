FROM ubuntu:latest

# Install packages from list
COPY packages.txt /tmp/
RUN apt-get update \
    && xargs -a /tmp/packages.txt apt-get install -y

RUN mkdir /var/run/sshd

# Install code-server
RUN curl -fsSL https://code-server.dev/install.sh | sh

# Install Jinja2 syntax highlighting extension for code-server
RUN code-server --install-extension samuelcolvin.jinjahtml

# Create a non-root user with explicit UID/GID 1000
# Remove existing user/group with UID/GID 1000 if present (usually 'ubuntu')
RUN (userdel -r ubuntu 2>/dev/null || true) && \
    (groupdel ubuntu 2>/dev/null || true) && \
    groupadd -g 1000 magent && \
    useradd -u 1000 -g 1000 -m -s /bin/bash magent

# Install Claude tools and Playwright globally (as root)
RUN npm install -g @anthropic-ai/sdk @anthropic-ai/claude-code playwright

# Install system dependencies for Playwright first (as root)
RUN npx playwright install-deps
RUN npx @modelcontextprotocol/server-puppeteer

# Install Docker CLI and add docker group
RUN apt-get update && apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg \
    && chmod a+r /etc/apt/keyrings/docker.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && apt-get update \
    && apt-get install -y docker-ce-cli

# Create docker group and add magent user to it
# Accept DOCKER_GID as build arg (defaults to 999 if not provided)
ARG DOCKER_GID=999
RUN groupadd -g ${DOCKER_GID} docker \
    && usermod -aG docker magent

# Install GitHub CLI (following official docs)
RUN (type -p wget >dev/null || (apt update && apt install wget -y)) \
    && mkdir -p -m 755 /etc/apt/keyrings \
    && out=$(mktemp) && wget -nv -O$out https://cli.github.com/packages/githubcli-archive-keyring.gpg \
    && cat $out | tee /etc/apt/keyrings/githubcli-archive-keyring.gpg > /dev/null \
    && chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg \
    && mkdir -p -m 755 /etc/apt/sources.list.d \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && apt update \
    && apt install gh -y

USER magent
WORKDIR /home/magent

# Create directories as magent user
RUN mkdir -p /home/magent/.config/gh \
    && mkdir -p /home/magent/.ssh \
    && mkdir -p /home/magent/.claude \
    && mkdir -p /home/magent/workspace

# Clone arthel repository from magent's fork
ARG ARTHEL_REPO_URL=https://github.com/magent-cryptograss/arthel.git
RUN git clone ${ARTHEL_REPO_URL} /home/magent/workspace/arthel

# Install dependencies for arthel
RUN cd /home/magent/workspace/arthel && npm install

USER root

# Copy startup script
COPY container_startup.py /usr/local/bin/
RUN chmod +x /usr/local/bin/container_startup.py

# CLAUDE.md will be symlinked from magenta repo on container startup

# Expose ports
EXPOSE 22 8080 4000 4050

CMD ["/usr/local/bin/container_startup.py"]
