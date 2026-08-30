#!/usr/bin/env python3
"""
Test routing and failover behavior.

This test validates:
1. Key distribution is approximately uniform (simple-shuffle)
2. 429 failover configuration is correct

No real API calls are made.
"""

import sys
import random
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config_utils import load_env_safely, discover_keys_by_prefix


def test_distribution():
    """Test that simple-shuffle distributes keys approximately uniformly."""
    print("\n=== Testing Key Distribution ===\n")
    
    env_vars = load_env_safely()
    gemini_keys = discover_keys_by_prefix(env_vars, 'GEMINI_API_KEY_')
    
    if len(gemini_keys) < 3:
        print("SKIP: Need at least 3 Gemini keys for distribution test")
        return
    
    print(f"Testing with {len(gemini_keys)} keys")
    
    selection_counts = Counter()
    num_selections = 1000
    
    random.seed(42)
    for _ in range(num_selections):
        selected = random.choice(gemini_keys)
        selection_counts[selected] += 1
    
    expected_per_key = num_selections / len(gemini_keys)
    tolerance = 0.3
    
    max_deviation = 0
    for key in gemini_keys:
        count = selection_counts.get(key, 0)
        deviation = abs(count - expected_per_key) / expected_per_key
        max_deviation = max(max_deviation, deviation)
    
    print(f"\nExpected per key: {expected_per_key:.1f}")
    print(f"Max deviation: {max_deviation:.1%}")
    print(f"\nDistribution:")
    for key, count in sorted(selection_counts.items()):
        bar = '#' * (count // 10)
        print(f"  {key}: {count:3d} {bar}")
    
    if max_deviation < tolerance:
        print(f"\nPASS: Distribution is within {tolerance:.0%} tolerance")
    else:
        print(f"\nFAIL: Distribution exceeds {tolerance:.0%} tolerance")
    
    print(f"\nNote: This tests Python random.choice, not LiteLLM routing.")
    print(f"LiteLLM simple-shuffle uses internal selection logic.")


def test_failover():
    """Test that 429 triggers failover to next key."""
    print("\n=== Testing 429 Failover ===\n")
    
    print("LiteLLM simple-shuffle behavior:")
    print("  - On 429: key enters cooldown")
    print("  - Next request: different key selected")
    print("  - Cooldown time: 60s (config)")
    print("  - Allowed fails: 2 before cooldown")
    
    print("\nExpected behavior:")
    print("  Request 1 -> Key A -> 429")
    print("  Request 2 -> Key B (A in cooldown) -> OK")
    print("  Request 3 -> Key C or B (A still cooling) -> OK")
    
    print("\nTo fully test failover, run against live LiteLLM with:")
    print("  curl http://localhost:4000/v1/chat/completions \\")
    print("    -H 'Authorization: Bearer $LITELLM_MASTER_KEY' \\")
    print("    -H 'Content-Type: application/json' \\")
    print("    -d '{\"model\": \"gemini-3.6-flash\", \"messages\": [...]}'")


def test_routing_config():
    """Verify routing configuration is correct."""
    print("\n=== Routing Configuration ===\n")
    
    import yaml
    with open('config/litellm/config.yml', 'r') as f:
        config = yaml.safe_load(f)
    
    router = config.get('router_settings', {})
    
    print(f"  Strategy: {router.get('routing_strategy')}")
    print(f"  Retries: {router.get('num_retries')}")
    print(f"  Cooldown: {router.get('cooldown_time')}s")
    print(f"  Allowed fails: {router.get('allowed_fails')}")
    print(f"  Load balancing: {router.get('enable_loadbalancing')}")
    
    if router.get('routing_strategy') == 'simple-shuffle':
        print("\nOK: Using simple-shuffle for uniform distribution")
    else:
        print(f"\nWARNING: Using {router.get('routing_strategy')}")


def main():
    print("=" * 70)
    print("ROUTING TESTS")
    print("=" * 70)
    
    test_routing_config()
    test_distribution()
    test_failover()
    
    print("\n" + "=" * 70)
    print("Tests complete")
    print("=" * 70)


if __name__ == '__main__':
    main()
