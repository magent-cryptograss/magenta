#!/usr/bin/env python3
"""
Container startup script for magenta-arthel containers.
Handles volume initialization, repository cloning, and service configuration.
"""

import os
import subprocess
import sys
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def run_command(cmd, cwd=None, check=True, user=None):
    """Run a shell command with proper error handling."""
    if user:
        cmd = f"su - {user} -c '{cmd}'"

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            check=check,
            capture_output=True,
            text=True
        )
        if result.stdout:
            logger.debug(result.stdout)
        return result
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {cmd}")
        logger.error(f"Error: {e.stderr}")
        if check:
            raise
        return e


def ensure_repo_cloned(repo_url, target_path, user='magent', run_install=False):
    """Clone repository if it doesn't exist, optionally run npm install."""
    target = Path(target_path)

    if target.exists():
        logger.info(f"✓ {target.name} already present at {target}")
        return False

    logger.info(f"Cloning {repo_url} to {target}...")
    target.parent.mkdir(parents=True, exist_ok=True)

    run_command(f"git clone {repo_url} {target}", user=user)
    logger.info(f"✓ Cloned {target.name}")

    if run_install and (target / 'package.json').exists():
        logger.info(f"Installing npm dependencies for {target.name}...")
        run_command("npm install", cwd=target, user=user)
        logger.info(f"✓ Installed dependencies for {target.name}")

    return True


def setup_symlink(source, target, description):
    """Create symlink if source exists and target doesn't."""
    source_path = Path(source)
    target_path = Path(target)

    if not source_path.exists():
        logger.warning(f"Source file not found: {source}")
        return False

    if target_path.exists() or target_path.is_symlink():
        logger.info(f"✓ {description} already exists")
        return False

    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.symlink_to(source_path)
    logger.info(f"✓ Created symlink: {description}")
    return True


def setup_workspace():
    """Initialize workspace with required repositories."""
    logger.info("=== Setting up workspace ===")

    workspace = Path("/home/magent/workspace")
    workspace.mkdir(parents=True, exist_ok=True)

    # Ensure magent owns the workspace directory
    run_command(f"chown -R magent:magent {workspace}")

    # Clone arthel (main development repo) - optional for local dev
    # Skip if SKIP_ARTHEL env var is set
    if os.getenv('SKIP_ARTHEL'):
        logger.info("Skipping arthel clone (SKIP_ARTHEL set)")
    else:
        ensure_repo_cloned(
            "https://github.com/jMyles/arthel.git",
            workspace / "arthel",
            user='magent',
            run_install=True
        )

    # Clone magenta (for CLAUDE.md and WAKEUP.md)
    ensure_repo_cloned(
        "https://github.com/magent-cryptograss/magenta.git",
        workspace / "magenta",
        user='magent',
        run_install=False
    )


def setup_claude_config():
    """Set up CLAUDE.md in home directory and ensure .claude directory exists."""
    logger.info("=== Setting up Claude configuration ===")

    # Ensure .claude directory exists for Claude Code's own use
    claude_dir = Path("/home/magent/.claude")
    claude_dir.mkdir(parents=True, exist_ok=True)

    # Symlink CLAUDE.md to home directory (where Claude Code launches)
    setup_symlink(
        "/home/magent/workspace/magenta/CLAUDE.md",
        "/home/magent/CLAUDE.md",
        "CLAUDE.md in home directory"
    )

    # Fix permissions
    logger.info("Fixing .claude directory permissions...")
    run_command("chown -R magent:magent /home/magent/.claude")
    run_command("chown magent:magent /home/magent/.claude.json", check=False)
    logger.info("✓ Permissions updated")


def configure_github_cli():
    """Configure GitHub CLI if GH_TOKEN is available."""
    logger.info("=== Configuring GitHub CLI ===")

    gh_token = os.environ.get('GH_TOKEN')
    if not gh_token:
        logger.info("No GH_TOKEN provided, skipping GitHub CLI setup")
        return

    logger.info("Authenticating GitHub CLI...")
    run_command(f"echo '{gh_token}' | gh auth login --with-token", user='magent')
    run_command("gh auth setup-git", user='magent')
    logger.info("✓ GitHub CLI authenticated")


def configure_mcp_server():
    """Configure MCP servers for Claude Code."""
    logger.info("=== Configuring MCP servers ===")

    # The MCP memory server runs in a separate container (mcp-server) on the magenta-net network
    # Connect to it via the service name
    run_command(
        "claude mcp add --scope user --transport http magenta-memory-v2 http://mcp-server:8000",
        user='magent',
        check=False  # Don't fail if already configured
    )
    logger.info("✓ MCP memory server configured: http://mcp-server:8000")

    # Add Playwright MCP server for browser automation via Docker
    run_command(
        "claude mcp add --scope user --transport stdio playwright 'docker run -i --rm --init --pull=always mcr.microsoft.com/playwright/mcp'",
        user='magent',
        check=False
    )
    logger.info("✓ Playwright MCP server configured (via Docker)")


def setup_environment_variables():
    """Export container environment variables to shell profile."""
    logger.info("=== Setting up environment variables ===")

    # Variables to export to shell sessions
    env_vars = [
        'DEVELOPER_NAME',
        'DEVELOPER_FULL_NAME',
        'DEVELOPER_EMAIL',
        'DEVELOPER_GITHUB',
        'POSTGRES_HOST',
        'POSTGRES_DB',
        'POSTGRES_USER',
        'POSTGRES_PASSWORD'
    ]

    bashrc_path = Path('/home/magent/.bashrc')

    # Read current .bashrc
    if bashrc_path.exists():
        with open(bashrc_path, 'r') as f:
            bashrc_content = f.read()
    else:
        bashrc_content = ''

    # Add environment exports if not already there
    exports_to_add = []
    for var in env_vars:
        value = os.environ.get(var)
        if value and f'export {var}=' not in bashrc_content:
            exports_to_add.append(f'export {var}="{value}"')

    if exports_to_add:
        with open(bashrc_path, 'a') as f:
            f.write('\n# Container environment variables\n')
            f.write('\n'.join(exports_to_add) + '\n')
        logger.info(f"✓ Added {len(exports_to_add)} environment variables to .bashrc")
    else:
        logger.info("✓ Environment variables already configured")


def start_services():
    """Start required services."""
    logger.info("=== Starting services ===")

    # Start SSH
    logger.info("Starting SSH service...")
    run_command("service ssh start")
    logger.info("✓ SSH started")

    # Note: PostgreSQL runs in separate container, not started here
    logger.info("✓ Using shared PostgreSQL container")


def main():
    """Main startup sequence."""
    logger.info("=" * 60)
    logger.info("Container startup beginning")
    logger.info("=" * 60)

    try:
        setup_workspace()
        setup_claude_config()
        setup_environment_variables()
        configure_github_cli()
        configure_mcp_server()
        start_services()

        logger.info("=" * 60)
        logger.info("✓ Container startup complete")
        logger.info("=" * 60)

        # Keep container running
        logger.info("Container ready. Keeping alive...")
        subprocess.run(["tail", "-f", "/dev/null"])

    except Exception as e:
        logger.error(f"Startup failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
