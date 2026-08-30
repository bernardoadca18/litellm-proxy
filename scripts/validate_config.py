#!/usr/bin/env python3
"""
Validate LiteLLM configuration for common errors:
- Duplicate deployments
- Missing environment variables
- Invalid YAML
- Configuration inconsistencies
"""

import yaml
import sys
import re
import os
from collections import defaultdict
from pathlib import Path


def load_config(config_path: str) -> dict:
    """Load and parse YAML config file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def find_duplicates(config: dict) -> list:
    """Find duplicate deployments (same model_name, provider_model, api_key)."""
    model_list = config.get('model_list', [])
    seen = defaultdict(list)
    duplicates = []

    for i, deployment in enumerate(model_list):
        model_name = deployment.get('model_name', '')
        litellm_params = deployment.get('litellm_params', {})
        provider_model = litellm_params.get('model', '')
        api_key = litellm_params.get('api_key', '')

        key = (model_name, provider_model, api_key)
        seen[key].append(i)

    for key, indices in seen.items():
        if len(indices) > 1:
            duplicates.append({
                'model_name': key[0],
                'provider_model': key[1],
                'api_key': key[2],
                'indices': indices
            })

    return duplicates


def find_env_vars(config: dict) -> set:
    """Find all environment variable references in config."""
    config_str = yaml.dump(config)
    pattern = r'os\.environ/([A-Za-z_][A-Za-z0-9_]*)'
    return set(re.findall(pattern, config_str))


def validate_env_vars(env_vars: set, config_path: str) -> list:
    """Check if referenced env vars are documented in .env.example."""
    config_dir = Path(config_path).parent
    env_example_path = config_dir.parent.parent / '.env.example'
    missing = []

    if env_example_path.exists():
        with open(env_example_path, 'r') as f:
            example_vars = set()
            for line in f:
                if '=' in line and not line.startswith('#'):
                    var_name = line.split('=')[0].strip()
                    if var_name:
                        example_vars.add(var_name)

        for var in env_vars:
            if var not in example_vars:
                missing.append(var)

    return missing


def check_router_settings(config: dict) -> list:
    """Check router settings for potential issues."""
    issues = []
    router = config.get('router_settings', {})

    strategy = router.get('routing_strategy', '')
    if strategy == 'least-busy':
        issues.append("Using 'least-busy' routing - consider 'simple-shuffle' for uniform distribution")

    num_retries = router.get('num_retries', 0)
    if num_retries > 3:
        issues.append(f"High retry count ({num_retries}) may cause latency issues")

    return issues


def check_cache_settings(config: dict) -> list:
    """Check cache settings."""
    issues = []
    litellm_settings = config.get('litellm_settings', {})

    if litellm_settings.get('cache') == True:
        issues.append("Response cache enabled - verify if needed for diverse prompts")

    return issues


def check_model_groups(config: dict) -> dict:
    """Analyze model groups and key distribution."""
    model_list = config.get('model_list', [])
    model_groups = defaultdict(lambda: {'keys': set(), 'providers': set()})

    for deployment in model_list:
        model_name = deployment.get('model_name', '')
        litellm_params = deployment.get('litellm_params', {})
        provider_model = litellm_params.get('model', '')
        api_key = litellm_params.get('api_key', '')

        provider = provider_model.split('/')[0] if '/' in provider_model else 'unknown'

        model_groups[model_name]['keys'].add(api_key)
        model_groups[model_name]['providers'].add(provider)

    return model_groups


def main():
    config_path = sys.argv[1] if len(sys.argv) > 1 else './config/litellm/config.yml'

    print("=" * 70)
    print("LITELLM CONFIG VALIDATION")
    print("=" * 70)
    print(f"\nValidating: {config_path}\n")

    errors = []
    warnings = []

    # Load config
    try:
        config = load_config(config_path)
        print("✅ YAML is valid")
    except yaml.YAMLError as e:
        print(f"❌ YAML parsing error: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"❌ Config file not found: {config_path}")
        sys.exit(1)

    # Check duplicates
    duplicates = find_duplicates(config)
    if duplicates:
        print(f"\n❌ DUPLICATES FOUND: {len(duplicates)}")
        for dup in duplicates:
            print(f"   - {dup['model_name']} + {dup['api_key']}")
            print(f"     Lines: {dup['indices']}")
        errors.append(f"{len(duplicates)} duplicate deployment(s)")
    else:
        print("✅ No duplicate deployments")

    # Check environment variables
    env_vars = find_env_vars(config)
    missing_env = validate_env_vars(env_vars, config_path)
    if missing_env:
        print(f"\n⚠️  ENV VARS not in .env.example: {len(missing_env)}")
        for var in sorted(missing_env):
            print(f"   - {var}")
        warnings.append(f"{len(missing_env)} undocumented env var(s)")
    else:
        print(f"✅ All {len(env_vars)} env vars documented")

    # Check router settings
    router_issues = check_router_settings(config)
    if router_issues:
        print("\n⚠️  ROUTER SETTINGS:")
        for issue in router_issues:
            print(f"   - {issue}")
        warnings.extend(router_issues)
    else:
        print("✅ Router settings look good")

    # Check cache settings
    cache_issues = check_cache_settings(config)
    if cache_issues:
        print("\n⚠️  CACHE SETTINGS:")
        for issue in cache_issues:
            print(f"   - {issue}")
        warnings.extend(cache_issues)

    # Model group summary
    model_groups = check_model_groups(config)
    print(f"\n📊 SUMMARY:")
    print(f"   Model groups: {len(model_groups)}")

    total_deployments = sum(len(g['keys']) for g in model_groups.values())
    print(f"   Total deployments: {total_deployments}")

    # Provider breakdown
    providers = defaultdict(int)
    for group in model_groups.values():
        for p in group['providers']:
            providers[p] += len(group['keys'])

    print(f"\n   By provider:")
    for p, count in sorted(providers.items(), key=lambda x: -x[1]):
        print(f"      {p}: {count}")

    # Final result
    print("\n" + "=" * 70)
    if errors:
        print("❌ VALIDATION FAILED")
        for e in errors:
            print(f"   ERROR: {e}")
        sys.exit(1)
    elif warnings:
        print("⚠️  VALIDATION PASSED WITH WARNINGS")
        for w in warnings:
            print(f"   WARNING: {w}")
        sys.exit(0)
    else:
        print("✅ VALIDATION PASSED")
        sys.exit(0)


if __name__ == '__main__':
    main()
