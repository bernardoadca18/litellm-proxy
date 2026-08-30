#!/usr/bin/env python3
"""
Analyze LiteLLM config.yml for issues:
- Duplicate deployments
- Count deployments per provider
- Detect configuration problems
"""

import yaml
import sys
from collections import defaultdict
from pathlib import Path

def analyze_config(config_path: str):
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    model_list = config.get('model_list', [])
    
    # Track deployments
    deployments = []
    deployment_keys = defaultdict(list)  # (model_name, provider_model) -> [api_keys]
    seen_deployments = defaultdict(list)  # (model_name, provider_model, api_key) -> [indices]
    
    # Provider counts
    provider_counts = defaultdict(lambda: defaultdict(int))  # provider -> model -> count
    
    # Model groups
    model_groups = defaultdict(list)
    
    for i, deployment in enumerate(model_list):
        model_name = deployment.get('model_name')
        litellm_params = deployment.get('litellm_params', {})
        provider_model = litellm_params.get('model', '')
        api_key = litellm_params.get('api_key', '')
        
        # Extract provider
        provider = provider_model.split('/')[0] if '/' in provider_model else 'unknown'
        
        deployments.append({
            'index': i,
            'model_name': model_name,
            'provider_model': provider_model,
            'api_key': api_key,
            'provider': provider
        })
        
        # Track for duplicates
        key = (model_name, provider_model, api_key)
        seen_deployments[key].append(i)
        
        # Track provider counts
        provider_counts[provider][model_name] += 1
        
        # Track model groups
        model_groups[model_name].append({
            'provider_model': provider_model,
            'api_key': api_key,
            'index': i
        })
    
    # Find duplicates
    duplicates = []
    for key, indices in seen_deployments.items():
        if len(indices) > 1:
            duplicates.append({
                'model_name': key[0],
                'provider_model': key[1],
                'api_key': key[2],
                'indices': indices
            })
    
    # Print report
    print("=" * 70)
    print("LITELLM CONFIG ANALYSIS REPORT")
    print("=" * 70)
    
    print(f"\n📊 SUMMARY:")
    print(f"   Total deployments: {len(deployments)}")
    print(f"   Unique model names: {len(model_groups)}")
    print(f"   Providers: {len(provider_counts)}")
    
    print(f"\n📦 DEPLOYMENTS BY PROVIDER:")
    total_by_provider = {}
    for provider in sorted(provider_counts.keys()):
        count = sum(provider_counts[provider].values())
        total_by_provider[provider] = count
        print(f"   {provider}: {count} deployments ({len(provider_counts[provider])} model groups)")
    
    print(f"\n📋 MODEL GROUPS BY PROVIDER:")
    for provider in sorted(provider_counts.keys()):
        print(f"\n   {provider.upper()}:")
        for model_name, count in sorted(provider_counts[provider].items()):
            print(f"      {model_name}: {count} keys")
    
    print(f"\n🔍 DUPLICATES FOUND: {len(duplicates)}")
    if duplicates:
        for dup in duplicates:
            print(f"   ❌ {dup['model_name']} + {dup['provider_model']} + {dup['api_key']}")
            print(f"      Indices: {dup['indices']}")
    else:
        print("   ✅ No duplicates found")
    
    print(f"\n📝 MODEL GROUPS DETAIL:")
    for model_name in sorted(model_groups.keys()):
        keys = model_groups[model_name]
        providers = set(k['provider_model'].split('/')[0] for k in keys)
        api_keys = set(k['api_key'] for k in keys)
        print(f"   {model_name}: {len(keys)} deployments")
        if len(providers) == 1:
            print(f"      Provider: {list(providers)[0]}")
        print(f"      Unique API keys: {len(api_keys)}")
    
    # Check for issues
    print(f"\n⚠️  ISSUES DETECTED:")
    issues = []
    
    if duplicates:
        issues.append(f"Found {len(duplicates)} duplicate deployment(s)")
    
    # Check for mismatched key counts within model groups
    for model_name, keys in model_groups.items():
        api_key_count = len(set(k['api_key'] for k in keys))
        if api_key_count != len(keys):
            pass  # This is expected for same model with different keys
    
    # Check router settings
    router_settings = config.get('router_settings', {})
    if router_settings.get('routing_strategy') == 'least-busy':
        issues.append("Using 'least-busy' routing - consider 'simple-shuffle' for uniform distribution")
    
    # Check for unused pgvector
    if 'gemini' not in provider_counts:
        issues.append("No Gemini models configured")
    
    # Check Redis cache
    litellm_settings = config.get('litellm_settings', {})
    if litellm_settings.get('cache') == True:
        issues.append("Response cache enabled - verify if needed for diverse prompts")
    
    if issues:
        for issue in issues:
            print(f"   - {issue}")
    else:
        print("   ✅ No issues detected")
    
    return {
        'total_deployments': len(deployments),
        'model_groups': len(model_groups),
        'duplicates': duplicates,
        'provider_counts': total_by_provider,
        'issues': issues
    }

if __name__ == '__main__':
    config_path = sys.argv[1] if len(sys.argv) > 1 else './config/litellm/config.yml'
    result = analyze_config(config_path)
    
    if result['duplicates']:
        sys.exit(1)
    sys.exit(0)
