"""API Testing Script for AudioImageCarrier Backend"""
import requests
import json
import time

BASE_URL = 'http://127.0.0.1:8000'
API_KEY = 'dev-test-key-12345'
headers = {'X-API-Key': API_KEY}

def test_health_check():
    """Test the health check endpoint"""
    print('='*60)
    print('TEST 1: Health Check')
    print('='*60)
    try:
        response = requests.get(f'{BASE_URL}/health', timeout=5)
        print(f'✅ Status Code: {response.status_code}')
        print(f'Response: {json.dumps(response.json(), indent=2)}')
        return True
    except Exception as e:
        print(f'❌ Error: {e}')
        return False

def test_root_endpoint():
    """Test the root endpoint"""
    print('\n' + '='*60)
    print('TEST 2: Root Endpoint')
    print('='*60)
    try:
        response = requests.get(f'{BASE_URL}/', timeout=5)
        print(f'✅ Status Code: {response.status_code}')
        print(f'Response: {json.dumps(response.json(), indent=2)}')
        return True
    except Exception as e:
        print(f'❌ Error: {e}')
        return False

def test_invalid_api_key():
    """Test authentication with invalid API key"""
    print('\n' + '='*60)
    print('TEST 3: Invalid API Key (Security Test)')
    print('='*60)
    try:
        response = requests.post(
            f'{BASE_URL}/api/v1/encode',
            headers={'X-API-Key': 'wrong-key'},
            timeout=5
        )
        print(f'Status Code: {response.status_code}')
        if response.status_code == 403:
            print('✅ Authentication working - 403 Forbidden for invalid key')
            return True
        else:
            print(f'❌ Expected 403, got {response.status_code}')
            return False
    except Exception as e:
        print(f'❌ Error: {e}')
        return False

def test_missing_api_key():
    """Test request without API key"""
    print('\n' + '='*60)
    print('TEST 4: Missing API Key (Security Test)')
    print('='*60)
    try:
        response = requests.post(f'{BASE_URL}/api/v1/encode', timeout=5)
        print(f'Status Code: {response.status_code}')
        if response.status_code in [401, 403]:
            print(f'✅ Authentication required - {response.status_code}')
            return True
        else:
            print(f'❌ Expected 401/403, got {response.status_code}')
            return False
    except Exception as e:
        print(f'❌ Error: {e}')
        return False

def main():
    """Run all tests"""
    print('\n🧪 AudioImageCarrier API Testing Suite')
    print(f'🔗 Base URL: {BASE_URL}')
    print(f'🔑 API Key: {API_KEY}\n')
    
    # Check if server is running
    try:
        requests.get(BASE_URL, timeout=2)
    except:
        print('❌ Server is not running!')
        print(f'Please start the server first: python -m uvicorn app.main:app --host 127.0.0.1 --port 8000')
        return
    
    results = []
    results.append(test_health_check())
    results.append(test_root_endpoint())
    results.append(test_invalid_api_key())
    results.append(test_missing_api_key())
    
    # Summary
    print('\n' + '='*60)
    print('TEST SUMMARY')
    print('='*60)
    passed = sum(results)
    total = len(results)
    print(f'Passed: {passed}/{total}')
    if passed == total:
        print('✅ All tests passed!')
    else:
        print(f'❌ {total - passed} test(s) failed')
    
    print(f'\n📖 Interactive API Documentation:')
    print(f'   Swagger UI: {BASE_URL}/docs')
    print(f'   ReDoc: {BASE_URL}/redoc')

if __name__ == '__main__':
    main()
