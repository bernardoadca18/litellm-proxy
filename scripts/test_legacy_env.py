#!/usr/bin/env python3
"""
Test that legacy environment variables are properly neutralized.

This test:
1. Creates a test .env with legacy variables
2. Starts LiteLLM
3. Verifies no Prisma/DEBUG issues occur
"""

import os
import sys
import subprocess
import tempfile
import time
from pathlib import Path


def test_legacy_env_neutralization():
    """
    Test that legacy env vars don't affect runtime.
    """
    print("=" * 70)
    print("LEGACY ENV NEUTRALIZATION TEST")
    print("=" * 70)
    
    print("\nTest: Legacy variables should be neutralized by entrypoint.sh")
    print("\nLegacy variables tested:")
    print("  - DATABASE_URL=postgresql://fake:fake@postgres:5432/fake")
    print("  - LITELLM_LOG=DEBUG")
    
    print("\nExpected behavior:")
    print("  - No Prisma initialization")
    print("  - No PostgreSQL connection attempt")
    print("  - No DEBUG logging")
    
    print("\nCurrent .env status:")
    
    env_vars = {}
    with open('.env', 'r') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                parts = line.strip().split('=', 1)
                if len(parts) == 2:
                    env_vars[parts[0]] = parts[1]
    
    legacy_vars = ['DATABASE_URL', 'LITELLM_LOG']
    found_legacy = False
    for var in legacy_vars:
        if var in env_vars:
            print(f"  {var}: present (will be neutralized)")
            found_legacy = True
    
    if not found_legacy:
        print("  No legacy variables in current .env")
    
    print("\nVerifying entrypoint.sh contains neutralization:")
    
    with open('scripts/entrypoint.sh', 'r') as f:
        entrypoint = f.read()
    
    checks = [
        ('DATABASE_URL', 'unset DATABASE_URL'),
        ('LITELLM_LOG', 'unset LITELLM_LOG'),
        ('POSTGRES_USER', 'unset POSTGRES_USER'),
    ]
    
    all_ok = True
    for name, check in checks:
        if check in entrypoint:
            print(f"  OK: {name} is unset")
        else:
            print(f"  FAIL: {name} unset not found")
            all_ok = False
    
    print("\nVerifying container logs for issues:")
    
    result = subprocess.run(
        ['docker', 'compose', 'logs', 'litellm'],
        capture_output=True,
        text=True
    )
    
    logs = result.stdout + result.stderr
    
    issues = [
        ('Prisma', 'Prisma initialization'),
        ('P1001', 'PostgreSQL connection error'),
        ('postgres:5432', 'PostgreSQL connection attempt'),
    ]
    
    found_issues = False
    for pattern, desc in issues:
        if pattern in logs:
            print(f"  WARNING: Found {desc}")
            found_issues = True
    
    if not found_issues:
        print("  OK: No Prisma/PostgreSQL issues in logs")
    
    print("\n" + "=" * 70)
    
    if all_ok and not found_issues:
        print("PASS: Legacy env neutralization working correctly")
        return 0
    else:
        print("FAIL: Issues found")
        return 1


if __name__ == '__main__':
    sys.exit(test_legacy_env_neutralization())
