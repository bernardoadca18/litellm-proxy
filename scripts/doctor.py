#!/usr/bin/env python3
"""
Diagnostic tool for LiteLLM Proxy.

Checks:
- Environment file exists
- Required variables are set
- Provider keys are configured
- Docker is available
- No legacy variables that could cause issues
"""

import os
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config_utils import (
    load_env_safely,
    get_master_key,
    has_any_provider_key,
    get_legacy_vars,
    print_key_counts,
)


def check_env_file(env_path: Path) -> bool:
    """Check if .env file exists."""
    if env_path.exists():
        print("OK: .env exists")
        return True
    else:
        print("ERROR: .env not found")
        return False


def check_master_key(env_vars: dict) -> bool:
    """Check if master key is configured."""
    master_key = get_master_key(env_vars)
    if master_key:
        print("OK: LITELLM_MASTER_KEY is set")
        return True
    else:
        print("ERROR: LITELLM_MASTER_KEY not set or empty")
        return False


def check_provider_keys(env_vars: dict) -> bool:
    """Check if at least one provider has keys configured."""
    if has_any_provider_key(env_vars):
        print("OK: At least one provider key is configured")
        print_key_counts(env_vars)
        return True
    else:
        print("WARNING: No provider keys configured")
        return False


def check_legacy_vars(env_vars: dict) -> bool:
    """Check for legacy variables that should be neutralized."""
    legacy = get_legacy_vars(env_vars)
    if legacy:
        print("WARNING: Legacy variables detected in .env (neutralized by entrypoint):")
        for var in legacy:
            print(f"  - {var}")
        return True
    else:
        print("OK: No legacy variables found")
        return False


def check_docker() -> bool:
    """Check if Docker is available."""
    import subprocess
    
    try:
        subprocess.run(['docker', '--version'], capture_output=True, check=True)
        print("OK: Docker is available")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("ERROR: Docker not found")
        return False
    
    try:
        subprocess.run(['docker', 'compose', 'version'], capture_output=True, check=True)
        print("OK: Docker Compose is available")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("ERROR: Docker Compose not found")
        return False


def check_port() -> bool:
    """Check if port 4000 is available."""
    import socket
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', 4000))
    sock.close()
    
    if result != 0:
        print("OK: Port 4000 is available")
        return True
    else:
        print("WARNING: Port 4000 may already be in use")
        return False


def main():
    parser = argparse.ArgumentParser(description='LiteLLM Proxy diagnostics')
    parser.add_argument('--preflight', action='store_true', 
                        help='Run preflight checks only (for make up)')
    args = parser.parse_args()
    
    project_root = Path(__file__).parent.parent
    env_path = project_root / '.env'
    
    if not args.preflight:
        print("=" * 70)
        print("LITELLM PROXY DIAGNOSTICS")
        print("=" * 70)
        print()
    
    errors = []
    warnings = []
    
    # Environment checks
    if not args.preflight:
        print("=== Environment ===")
    if not check_env_file(env_path):
        errors.append(".env not found")
    
    env_vars = load_env_safely(env_path)
    
    if not args.preflight:
        print()
        print("=== Required Variables ===")
    if not check_master_key(env_vars):
        errors.append("LITELLM_MASTER_KEY not set")
    
    if not args.preflight:
        print()
        print("=== Provider Keys ===")
    if not check_provider_keys(env_vars):
        warnings.append("No provider keys configured")
    
    if not args.preflight:
        print()
        print("=== Legacy Variables ===")
    check_legacy_vars(env_vars)
    
    if not args.preflight:
        print()
        print("=== Docker ===")
    if not check_docker():
        errors.append("Docker not available")
    
    if not args.preflight:
        print()
        print("=== Port Availability ===")
    check_port()
    
    if not args.preflight:
        print()
        print("=" * 70)
    
    if errors:
        if not args.preflight:
            print("FAILED: Critical issues found")
            for e in errors:
                print(f"  ERROR: {e}")
        sys.exit(1)
    elif warnings and not args.preflight:
        print("PASSED with warnings")
        sys.exit(0)
    elif not args.preflight:
        print("PASSED")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
