#!/usr/bin/env python3
"""
Generate LiteLLM config.yml from providers.yml.

This script reads config/providers.yml and generates config/litellm/config.yml.
It discovers API keys from .env by prefix pattern (never reads values).

Usage:
    python scripts/generate_config.py
"""

import yaml
import os
import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent))
from config_utils import load_env_safely, discover_keys_by_prefix


def load_providers(providers_path: str) -> dict:
    with open(providers_path, 'r') as f:
        return yaml.safe_load(f)


def generate_model_list(providers: dict, env_vars: dict) -> list:
    model_list = []
    
    providers_config = providers.get('providers', {})
    
    for provider_name, provider_config in providers_config.items():
        key_prefix = provider_config.get('key_prefix', '')
        models = provider_config.get('models', [])
        
        if not key_prefix:
            continue
        
        available_keys = discover_keys_by_prefix(env_vars, key_prefix)
        
        if not available_keys:
            continue
        
        for model in models:
            model_name = model.get('name')
            provider_model = model.get('model')
            mode = model.get('mode', 'chat')
            rpm = model.get('rpm')
            tpm = model.get('tpm')
            timeout = model.get('timeout')
            supports_fc = model.get('supports_function_calling')
            
            for key_name in available_keys:
                deployment = {
                    'model_name': model_name,
                    'litellm_params': {
                        'model': provider_model,
                        'api_key': f'os.environ/{key_name}',
                    },
                    'model_info': {
                        'mode': mode,
                    }
                }
                
                if supports_fc is True:
                    deployment['model_info']['supports_function_calling'] = True
                
                if rpm is not None:
                    deployment['litellm_params']['rpm'] = rpm
                if tpm is not None:
                    deployment['litellm_params']['tpm'] = tpm
                if timeout is not None:
                    deployment['litellm_params']['timeout'] = timeout
                
                model_list.append(deployment)
    
    return model_list


def generate_ollama_models(ollama_config: dict) -> list:
    model_list = []
    models = ollama_config.get('models', [])
    
    for model in models:
        model_name = model.get('name')
        provider_model = model.get('model')
        mode = model.get('mode', 'chat')
        api_base = model.get('api_base', 'os.environ/OLLAMA_API_BASE')
        timeout = model.get('timeout')
        info = model.get('info', {})
        
        deployment = {
            'model_name': model_name,
            'litellm_params': {
                'model': provider_model,
                'api_base': api_base,
            },
            'model_info': info if info else {'mode': mode},
        }
        
        if 'mode' not in deployment['model_info']:
            deployment['model_info']['mode'] = mode
        
        if timeout is not None:
            deployment['litellm_params']['timeout'] = timeout
        
        model_list.append(deployment)
    
    return model_list


def generate_router_settings(providers: dict) -> dict:
    router = providers.get('router', {})
    return {
        'routing_strategy': router.get('routing_strategy', 'simple-shuffle'),
        'num_retries': router.get('num_retries', 2),
        'request_timeout': router.get('request_timeout', 90),
        'cooldown_time': router.get('cooldown_time', 60),
        'allowed_fails': router.get('allowed_fails', 2),
        'retry_after': router.get('retry_after', 5),
        'enable_loadbalancing': router.get('enable_loadbalancing', True),
    }


def generate_litellm_settings(providers: dict) -> dict:
    settings = providers.get('settings', {})
    return {
        'num_retries': settings.get('num_retries', 2),
        'request_timeout': settings.get('request_timeout', 90),
        'allowed_fails': settings.get('allowed_fails', 2),
        'cache': False,
    }


def generate_general_settings(providers: dict) -> dict:
    return {
        'log_level': 'WARNING',
        'max_parallel_requests': 100,
        'master_key': 'os.environ/LITELLM_MASTER_KEY',
        'disable_prerun': True,
        'enable_jwt_auth': False,
    }


def main():
    project_root = Path(__file__).parent.parent
    providers_path = project_root / 'config' / 'providers.yml'
    config_path = project_root / 'config' / 'litellm' / 'config.yml'
    env_path = project_root / '.env'
    
    print("=" * 70)
    print("LITELLM CONFIG GENERATOR")
    print("=" * 70)
    print(f"\nSource: {providers_path}")
    print(f"Output: {config_path}")
    
    providers = load_providers(providers_path)
    env_vars = load_env_safely(env_path)
    
    model_list = generate_model_list(providers, env_vars)
    
    ollama_config = providers.get('ollama', {})
    if ollama_config:
        ollama_models = generate_ollama_models(ollama_config)
        model_list.extend(ollama_models)
    
    if not model_list:
        print("\nWARNING: No models generated. Check if API keys are configured in .env")
        return 1
    
    config = {
        'model_list': model_list,
        'router_settings': generate_router_settings(providers),
        'litellm_settings': generate_litellm_settings(providers),
        'general_settings': generate_general_settings(providers),
    }
    
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
    
    print(f"\nGenerated {len(model_list)} deployments")
    
    by_provider = defaultdict(int)
    by_mode = defaultdict(int)
    for deployment in model_list:
        model = deployment.get('litellm_params', {}).get('model', '')
        provider = model.split('/')[0] if '/' in model else 'unknown'
        by_provider[provider] += 1
        
        mode = deployment.get('model_info', {}).get('mode', 'chat')
        by_mode[mode] += 1
    
    print("\nBy provider:")
    for provider, count in sorted(by_provider.items(), key=lambda x: -x[1]):
        print(f"  {provider}: {count}")
    
    print("\nBy mode:")
    for mode, count in sorted(by_mode.items(), key=lambda x: -x[1]):
        print(f"  {mode}: {count}")
    
    print(f"\nConfig written to: {config_path}")
    print("=" * 70)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
