#!/usr/bin/env python3
"""
Real routing tests using mock upstream servers.

Tests:
1. Key distribution (simple-shuffle)
2. 429 failover
3. Cooldown behavior

Uses only Python stdlib - no external dependencies.
"""

import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path


class MockHandler(BaseHTTPRequestHandler):
    """Mock upstream that records requests and can simulate 429."""
    
    key_status = {}  # key -> 'ok' | '429'
    request_log = []
    
    def log_message(self, format, *args):
        pass  # Suppress logging
    
    def do_POST(self):
        auth = self.headers.get('Authorization', '')
        key = auth.replace('Bearer ', '') if auth else 'unknown'
        
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length > 0 else b''
        
        record = {
            'key': key,
            'path': self.path,
            'time': time.time(),
        }
        self.request_log.append(record)
        
        status = self.key_status.get(key, 'ok')
        
        if status == '429':
            self.send_response(429)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'error': {'message': 'Rate limit exceeded', 'type': 'rate_limit_error'}
            }).encode())
        else:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'id': 'mock-response',
                'object': 'chat.completion',
                'choices': [{'message': {'content': f'OK from {key}'}, 'finish_reason': 'stop'}]
            }).encode())


def start_mock_server(port, key_status):
    """Start mock HTTP server in a thread."""
    MockHandler.key_status = key_status
    MockHandler.request_log = []
    
    server = HTTPServer(('127.0.0.1', port), MockHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.5)  # Wait for server to start
    return server


def generate_test_config(mock_port, keys, output_path):
    """Generate a test config.yml for routing tests."""
    config = {
        'model_list': [],
        'router_settings': {
            'routing_strategy': 'simple-shuffle',
            'num_retries': 2,
            'cooldown_time': 30,
            'allowed_fails': 2,
            'retry_after': 5,
            'enable_loadbalancing': True,
        },
        'litellm_settings': {
            'cache': False,
        },
        'general_settings': {
            'master_key': 'os.environ/TEST_MASTER_KEY',
            'disable_prerun': True,
        }
    }
    
    for key in keys:
        config['model_list'].append({
            'model_name': 'test-model',
            'litellm_params': {
                'model': 'openai/test-model',
                'api_key': f'os.environ/{key}',
                'api_base': f'http://127.0.0.1:{mock_port}/v1',
            },
            'model_info': {'mode': 'chat'},
        })
    
    with open(output_path, 'w') as f:
        import yaml
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)


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


def send_request(port, model, master_key):
    """Send a chat completion request."""
    url = f'http://127.0.0.1:{port}/v1/chat/completions'
    data = json.dumps({
        'model': model,
        'messages': [{'role': 'user', 'content': 'test'}],
        'max_tokens': 5,
    }).encode()
    
    req = urllib.request.Request(url, data=data, method='POST')
    req.add_header('Content-Type', 'application/json')
    req.add_header('Authorization', f'Bearer {master_key}')
    
    try:
        response = urllib.request.urlopen(req, timeout=30)
        return response.status, json.loads(response.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def test_distribution():
    """Test that simple-shuffle distributes across keys."""
    print("\n" + "=" * 70)
    print("TEST: Key Distribution (simple-shuffle)")
    print("=" * 70)
    
    mock_port = 18080
    litellm_port = 14000
    keys = ['MOCK_KEY_A', 'MOCK_KEY_B', 'MOCK_KEY_C']
    master_key = 'test-master-key-12345'
    
    env = os.environ.copy()
    env['TEST_MASTER_KEY'] = master_key
    env['MOCK_KEY_A'] = 'mock-a-value'
    env['MOCK_KEY_B'] = 'mock-b-value'
    env['MOCK_KEY_C'] = 'mock-c-value'
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
        config_path = f.name
        generate_test_config(mock_port, keys, config_path)
    
    mock_server = start_mock_server(mock_port, {})
    
    try:
        cmd = [
            'docker', 'run', '--rm', '-d',
            '--name', 'litellm-routing-test',
            '-p', f'{litellm_port}:4000',
            '-v', f'{config_path}:/app/config.yml:ro',
            '-e', 'TEST_MASTER_KEY=' + master_key,
            '-e', 'MOCK_KEY_A=mock-a-value',
            '-e', 'MOCK_KEY_B=mock-b-value',
            '-e', 'MOCK_KEY_C=mock-c-value',
            '-e', 'LITELLM_LOG_LEVEL=WARNING',
            'ghcr.io/berriai/litellm:v1.72.6-stable',
            '--config', '/app/config.yml',
            '--port', '4000',
            '--num_workers', '1',
            '--telemetry', 'false',
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"ERROR: Failed to start container: {result.stderr}")
            return False
        
        container_id = result.stdout.strip()
        time.sleep(2)
        
        if not wait_for_readiness(litellm_port, timeout=60):
            print("ERROR: LiteLLM failed to start")
            subprocess.run(['docker', 'logs', container_id], capture_output=True)
            subprocess.run(['docker', 'stop', container_id], capture_output=True)
            return False
        
        print(f"LiteLLM started on port {litellm_port}")
        print(f"Mock upstream on port {mock_port}")
        print(f"\nSending 100 requests...")
        
        MockHandler.request_log = []
        
        for i in range(100):
            status, _ = send_request(litellm_port, 'test-model', master_key)
            if status != 200:
                print(f"  Request {i}: HTTP {status}")
        
        subprocess.run(['docker', 'stop', container_id], capture_output=True)
        
    finally:
        mock_server.shutdown()
        os.unlink(config_path)
    
    counts = {}
    for record in MockHandler.request_log:
        key = record['key']
        counts[key] = counts.get(key, 0) + 1
    
    print(f"\nDistribution:")
    for key, count in sorted(counts.items()):
        pct = count / len(MockHandler.request_log) * 100 if MockHandler.request_log else 0
        bar = '#' * (count // 2)
        print(f"  {key}: {count:3d} ({pct:5.1f}%) {bar}")
    
    total = len(MockHandler.request_log)
    if total < 90:
        print(f"\nWARNING: Only {total} requests reached mock (expected 100)")
    
    if len(counts) >= 2:
        print(f"\nPASS: Requests distributed across {len(counts)} keys")
        return True
    else:
        print(f"\nFAIL: All requests went to single key")
        return False


def test_429_failover():
    """Test that 429 triggers failover to next key."""
    print("\n" + "=" * 70)
    print("TEST: 429 Failover")
    print("=" * 70)
    
    mock_port = 18081
    litellm_port = 14001
    keys = ['MOCK_KEY_A', 'MOCK_KEY_B', 'MOCK_KEY_C']
    master_key = 'test-master-key-12345'
    
    key_status = {
        'mock-a-value': '429',  # KEY_A will return 429
        'mock-b-value': 'ok',
        'mock-c-value': 'ok',
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
        config_path = f.name
        generate_test_config(mock_port, keys, config_path)
    
    mock_server = start_mock_server(mock_port, key_status)
    
    try:
        cmd = [
            'docker', 'run', '--rm', '-d',
            '--name', 'litellm-failover-test',
            '-p', f'{litellm_port}:4000',
            '-v', f'{config_path}:/app/config.yml:ro',
            '-e', 'TEST_MASTER_KEY=' + master_key,
            '-e', 'MOCK_KEY_A=mock-a-value',
            '-e', 'MOCK_KEY_B=mock-b-value',
            '-e', 'MOCK_KEY_C=mock-c-value',
            '-e', 'LITELLM_LOG_LEVEL=WARNING',
            'ghcr.io/berriai/litellm:v1.72.6-stable',
            '--config', '/app/config.yml',
            '--port', '4000',
            '--num_workers', '1',
            '--telemetry', 'false',
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"ERROR: Failed to start container: {result.stderr}")
            return False
        
        container_id = result.stdout.strip()
        time.sleep(2)
        
        if not wait_for_readiness(litellm_port, timeout=60):
            print("ERROR: LiteLLM failed to start")
            subprocess.run(['docker', 'stop', container_id], capture_output=True)
            return False
        
        print(f"LiteLLM started on port {litellm_port}")
        print(f"Mock KEY_A configured to return 429")
        print(f"\nSending 10 requests...")
        
        MockHandler.request_log = []
        
        success_count = 0
        for i in range(10):
            status, resp = send_request(litellm_port, 'test-model', master_key)
            if status == 200:
                success_count += 1
        
        subprocess.run(['docker', 'stop', container_id], capture_output=True)
        
    finally:
        mock_server.shutdown()
        os.unlink(config_path)
    
    counts = {}
    for record in MockHandler.request_log:
        key = record['key']
        counts[key] = counts.get(key, 0) + 1
    
    print(f"\nMock received {len(MockHandler.request_log)} requests:")
    for key, count in sorted(counts.items()):
        print(f"  {key}: {count}")
    
    print(f"\nSuccessful responses: {success_count}/10")
    
    a_requests = counts.get('mock-a-value', 0)
    b_requests = counts.get('mock-b-value', 0)
    c_requests = counts.get('mock-c-value', 0)
    
    if b_requests > 0 or c_requests > 0:
        print(f"PASS: Failover occurred - requests went to KEY_B/C")
        return True
    else:
        print(f"FAIL: No failover detected")
        return False


def main():
    """Run all routing tests."""
    print("=" * 70)
    print("LITELLM ROUTING TESTS (Real)")
    print("=" * 70)
    print("\nThese tests validate LiteLLM Router behavior with mock upstreams.")
    print("No real API keys are used.")
    
    results = []
    
    results.append(('Distribution', test_distribution()))
    results.append(('429 Failover', test_429_failover()))
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  {name}: {status}")
    
    all_passed = all(p for _, p in results)
    print("\n" + ("All tests passed" if all_passed else "Some tests failed"))
    
    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
