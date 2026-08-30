#!/usr/bin/env python3
"""
Test legacy environment variable neutralization.

Creates an isolated environment with legacy DATABASE_URL and LITELLM_LOG=DEBUG,
starts LiteLLM, and verifies no Prisma/Postgres/DEBUG issues occur.
"""

import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path


def wait_for_readiness(port, timeout=60):
    """Wait for LiteLLM to be ready."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            req = urllib.request.urlopen(f'http://127.0.0.1:{port}/health/readiness', timeout=5)
            if req.status == 200:
                return True
        except:
            pass
        time.sleep(1)
    return False


def test_legacy_env():
    """
    Test that legacy env vars are neutralized by entrypoint.sh.
    """
    print("=" * 70)
    print("LEGACY ENV NEUTRALIZATION TEST")
    print("=" * 70)
    
    print("\nInjecting legacy variables:")
    print("  DATABASE_URL=postgresql://fake:fake@postgres:5432/fake")
    print("  LITELLM_LOG=DEBUG")
    print("  POSTGRES_USER=fake_user")
    
    port = 14002
    container_name = 'litellm-legacy-test'
    
    test_markers = {
        'TEST_MASTER_KEY': 'test-master-legacy-12345',
        'TEST_GEMINI_KEY': 'test-gemini-legacy-67890',
    }
    
    env_vars = {
        'LITELLM_MASTER_KEY': test_markers['TEST_MASTER_KEY'],
        'GEMINI_API_KEY_1': test_markers['TEST_GEMINI_KEY'],
        'DATABASE_URL': 'postgresql://fake:fake@postgres:5432/fake',
        'LITELLM_LOG': 'DEBUG',
        'POSTGRES_USER': 'fake_user',
        'POSTGRES_PASSWORD': 'fake_pass',
        'LITELLM_LOG_LEVEL': 'WARNING',
    }
    
    config_content = """
model_list:
  - model_name: gemini-test
    litellm_params:
      model: gemini/gemini-3.6-flash
      api_key: os.environ/GEMINI_API_KEY_1

router_settings:
  routing_strategy: simple-shuffle
  num_retries: 2
  cooldown_time: 60

litellm_settings:
  cache: false

general_settings:
  master_key: os.environ/LITELLM_MASTER_KEY
  disable_prerun: true
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
        config_path = f.name
        f.write(config_content)
    
    try:
        cmd = ['docker', 'run', '--rm', '-d',
               '--name', container_name,
               '-p', f'{port}:4000',
               '-v', f'{config_path}:/app/config.yml:ro']
        
        for key, value in env_vars.items():
            cmd.extend(['-e', f'{key}={value}'])
        
        cmd.extend([
            '-e', 'LITELLM_LOG_LEVEL=WARNING',
            'ghcr.io/berriai/litellm:v1.72.6-stable',
            '--config', '/app/config.yml',
            '--port', '4000',
            '--num_workers', '1',
            '--telemetry', 'false',
        ])
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"\nERROR: Failed to start container: {result.stderr}")
            return False
        
        container_id = result.stdout.strip()
        time.sleep(3)
        
        if not wait_for_readiness(port, timeout=60):
            print("\nERROR: LiteLLM failed to start")
            logs = subprocess.run(['docker', 'logs', container_name], capture_output=True, text=True)
            print(f"Logs:\n{logs.stdout[-2000:]}")
            subprocess.run(['docker', 'stop', container_name], capture_output=True)
            return False
        
        print("\nLiteLLM started successfully")
        
        logs_result = subprocess.run(['docker', 'logs', container_name], capture_output=True, text=True)
        logs = logs_result.stdout + logs_result.stderr
        
        issues = []
        
        patterns = [
            ('Prisma schema loaded', 'Prisma initialized'),
            ('P1001', 'PostgreSQL connection error'),
            ('postgres:5432', 'PostgreSQL connection attempt'),
            ('Datasource "client"', 'Database datasource configured'),
            ('LiteLLM Proxy:DEBUG', 'DEBUG logging active'),
        ]
        
        for pattern, desc in patterns:
            if pattern in logs:
                issues.append(f"Found: {desc}")
        
        print("\nChecking logs for issues:")
        for pattern, desc in patterns:
            found = pattern in logs
            status = "FOUND - BAD" if found else "not found - OK"
            print(f"  {desc}: {status}")
        
        print("\nChecking for secret markers in logs:")
        for name, marker in test_markers.items():
            if marker in logs:
                issues.append(f"Secret marker {name} found in logs")
                print(f"  {name}: FOUND IN LOGS - BAD")
            else:
                print(f"  {name}: not found - OK")
        
        subprocess.run(['docker', 'stop', container_name], capture_output=True)
        
    finally:
        os.unlink(config_path)
    
    print("\n" + "=" * 70)
    
    if issues:
        print("FAIL: Issues found:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    else:
        print("PASS: Legacy env vars properly neutralized")
        return True


def main():
    success = test_legacy_env()
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
