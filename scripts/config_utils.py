"""
Shared configuration utilities for LiteLLM Proxy.

This module provides common functions for:
- Loading .env files safely (never prints secrets)
- Discovering provider keys by prefix
- Validating configuration
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional

try:
    from dotenv import dotenv_values
    HAS_DOTENV = True
except ImportError:
    HAS_DOTENV = False


def is_non_empty_secret(value: Optional[str]) -> bool:
    """Check if a value is a non-empty secret (not None, not empty, not quoted empty)."""
    if value is None:
        return False
    stripped = value.strip()
    if not stripped:
        return False
    if stripped in ('""', "''"):
        return False
    return True


def load_env_safely(env_path: Optional[str] = None) -> Dict[str, str]:
    """
    Load .env file and return dict of non-empty values.
    Never prints or exposes secret values.
    """
    if env_path is None:
        env_path = Path(__file__).parent.parent / '.env'
    
    result = {}
    
    if HAS_DOTENV and os.path.exists(env_path):
        values = dotenv_values(env_path)
        for key, value in values.items():
            if is_non_empty_secret(value):
                result[key] = value
    elif os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    parts = line.split('=', 1)
                    if len(parts) == 2:
                        key = parts[0].strip()
                        value = parts[1].strip()
                        if is_non_empty_secret(value):
                            result[key] = value
    
    return result


def discover_keys_by_prefix(env_vars: Dict[str, str], prefix: str) -> List[str]:
    """
    Discover all keys matching a prefix, sorted numerically.
    
    Example:
        prefix = "GEMINI_API_KEY_"
        returns: ["GEMINI_API_KEY_1", "GEMINI_API_KEY_2", "GEMINI_API_KEY_12"]
    """
    matching = []
    pattern = re.compile(rf'^{re.escape(prefix)}(\d+)$')
    
    for key in env_vars.keys():
        match = pattern.match(key)
        if match:
            matching.append((key, int(match.group(1))))
    
    matching.sort(key=lambda x: x[1])
    return [key for key, _ in matching]


def count_keys_by_prefix(env_vars: Dict[str, str], prefix: str) -> int:
    """Count non-empty keys matching a prefix."""
    return len(discover_keys_by_prefix(env_vars, prefix))


def get_master_key(env_vars: Dict[str, str]) -> Optional[str]:
    """Get LITELLM_MASTER_KEY if set and non-empty."""
    return env_vars.get('LITELLM_MASTER_KEY')


def has_any_provider_key(env_vars: Dict[str, str]) -> bool:
    """Check if at least one provider has configured keys."""
    prefixes = ['GEMINI_API_KEY_', 'OPENROUTER_API_KEY_', 'GROQ_API_KEY_']
    for prefix in prefixes:
        if discover_keys_by_prefix(env_vars, prefix):
            return True
    return False


def get_legacy_vars(env_vars: Dict[str, str]) -> List[str]:
    """
    Get list of legacy variables that exist in env.
    These are variables from old .env files that should be neutralized.
    """
    legacy_patterns = [
        'DATABASE_URL',
        'DIRECT_URL',
        'LITELLM_LOG',
        'LITELLM_METRICS_PORT',
        'POSTGRES_USER',
        'POSTGRES_PASSWORD',
        'POSTGRES_DB',
        'POSTGRES_PORT',
        'REDIS_PASSWORD',
        'GRAFANA_ADMIN_USER',
        'GRAFANA_ADMIN_PASSWORD',
        'PROMETHEUS_ENDPOINT',
        'ENABLE_PROMETHEUS',
        'ENABLE_OTEL',
        'MONITOR_INTERVAL',
        'PGADMIN_DEFAULT_EMAIL',
        'PGADMIN_DEFAULT_PASSWORD',
    ]
    
    found = []
    for var in legacy_patterns:
        if var in env_vars:
            found.append(var)
    
    return found


def print_key_counts(env_vars: Dict[str, str]) -> None:
    """Print count of configured keys per provider (never prints values)."""
    providers = [
        ('Gemini', 'GEMINI_API_KEY_'),
        ('OpenRouter', 'OPENROUTER_API_KEY_'),
        ('Groq', 'GROQ_API_KEY_'),
    ]
    
    for name, prefix in providers:
        count = count_keys_by_prefix(env_vars, prefix)
        print(f"  {name} keys configured: {count}")
