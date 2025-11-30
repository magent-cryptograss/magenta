"""
Secrets filtering to prevent leaking sensitive data.

Loads secrets from Ansible vault and provides scrubbing functions
to redact those secrets from text, JSON, and other data structures
before they're written to databases, sent to external APIs, etc.
"""

import os
import re
import json
import yaml
import subprocess
import logging
from pathlib import Path
from typing import Any, Dict, List, Union

logger = logging.getLogger(__name__)


class SecretsFilter:
    """
    Filter for redacting secrets from text and data structures.

    Loads secrets from Ansible vault and provides methods to scrub
    sensitive values before they're persisted or transmitted.
    """

    def __init__(self, vault_path: str = None, vault_password: str = None, secrets_json: str = None):
        """
        Initialize the secrets filter.

        Args:
            vault_path: Path to encrypted Ansible vault file
            vault_password: Password to decrypt vault (reads from env if not provided)
            secrets_json: JSON-encoded list of secrets (alternative to vault)
        """
        self.secrets: List[str] = []
        self.redaction_text = "[REDACTED:VAULT_SECRET]"

        # First try loading from JSON (preferred - no vault password needed at runtime)
        if secrets_json:
            self._load_from_json(secrets_json)
        elif vault_path:
            self._load_vault_secrets(vault_path, vault_password)

        logger.info(f"SecretsFilter initialized with {len(self.secrets)} secret values to scrub")

    def _load_from_json(self, secrets_json: str):
        """Load secrets from a JSON-encoded list."""
        try:
            secrets_list = json.loads(secrets_json)
            if isinstance(secrets_list, list):
                self.secrets = [s for s in secrets_list if isinstance(s, str) and s]
                logger.info(f"Loaded {len(self.secrets)} secrets from JSON")
            else:
                logger.warning("SCRUB_SECRETS is not a JSON list")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse secrets JSON: {e}")

    def _load_vault_secrets(self, vault_path: str, vault_password: str = None):
        """
        Load secrets from encrypted Ansible vault.

        Decrypts the vault and extracts all vault_* variable values
        to build the list of secrets to scrub.
        """
        vault_path = Path(vault_path)
        if not vault_path.exists():
            logger.warning(f"Vault file not found: {vault_path}")
            return

        # Get vault password from parameter or environment
        password = vault_password or os.environ.get('ANSIBLE_VAULT_PASSWORD')
        if not password:
            logger.warning("No vault password provided, skipping vault secrets loading")
            return

        try:
            # Decrypt vault using ansible-vault
            result = subprocess.run(
                ['ansible-vault', 'view', str(vault_path)],
                input=password.encode(),
                capture_output=True,
                check=True
            )

            # Parse decrypted YAML
            vault_data = yaml.safe_load(result.stdout)

            # Extract all vault_* variable values
            for key, value in vault_data.items():
                if key.startswith('vault_') and isinstance(value, str) and value:
                    # Add the secret value
                    self.secrets.append(value)
                    logger.debug(f"Loaded secret from vault variable: {key}")

            logger.info(f"Loaded {len(self.secrets)} secrets from vault")

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to decrypt vault: {e.stderr.decode()}")
        except Exception as e:
            logger.error(f"Error loading vault secrets: {e}")

    def scrub(self, text: str) -> str:
        """
        Scrub secrets from a text string.

        Args:
            text: String that may contain secrets

        Returns:
            String with secrets replaced by redaction text
        """
        if not text:
            return text

        result = text
        for secret in self.secrets:
            if secret in result:
                result = result.replace(secret, self.redaction_text)

        return result

    def scrub_json(self, data: Union[Dict, List, Any]) -> Union[Dict, List, Any]:
        """
        Recursively scrub secrets from JSON-like data structures.

        Args:
            data: Dict, list, or primitive value

        Returns:
            Same structure with secrets scrubbed
        """
        if isinstance(data, dict):
            return {k: self.scrub_json(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self.scrub_json(item) for item in data]
        elif isinstance(data, str):
            return self.scrub(data)
        else:
            return data

    def scrub_jsonl_line(self, line: str) -> str:
        """
        Scrub secrets from a JSONL line.

        Parses the JSON, scrubs it, and returns as JSONL string.

        Args:
            line: JSONL line (JSON object as string)

        Returns:
            Scrubbed JSONL line
        """
        try:
            data = json.loads(line)
            scrubbed = self.scrub_json(data)
            return json.dumps(scrubbed)
        except json.JSONDecodeError:
            # If it's not valid JSON, just scrub as text
            return self.scrub(line)

    def add_secret(self, secret: str):
        """
        Manually add a secret value to scrub.

        Useful for runtime-discovered secrets or environment variables.
        """
        if secret and secret not in self.secrets:
            self.secrets.append(secret)
            logger.debug(f"Added secret to filter (length: {len(secret)})")

    def add_env_secrets(self, *env_var_names: str):
        """
        Add secrets from environment variables.

        Args:
            *env_var_names: Names of environment variables containing secrets
        """
        for var_name in env_var_names:
            value = os.environ.get(var_name)
            if value:
                self.add_secret(value)
                logger.debug(f"Added secret from env var: {var_name}")
