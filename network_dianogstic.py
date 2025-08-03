#!/usr/bin/env python3
"""
Network Diagnostic Tool for Google OAuth Issues
Run this to diagnose network connectivity problems
"""

import requests
import socket
import time
import json
from urllib.parse import urlparse

def test_dns_resolution():
    """Test DNS resolution for Google services"""
    print("🔍 Testing DNS Resolution...")
    
    hosts_to_test = [
        'accounts.google.com',
        'www.googleapis.com',
        'oauth2.googleapis.com',
        'google.com'
    ]
    
    dns_results = {}
    
    for host in hosts_to_test:
        try:
            ip = socket.gethostbyname(host)
            dns_results[host] = f"✅ Resolved to {ip}"
            print(f"  {host}: ✅ {ip}")
        except socket.gaierror as e:
            dns_results[host] = f"❌ DNS Error: {e}"
            print(f"  {host}: ❌ DNS Error: {e}")
    
    return dns_results

def test_basic_connectivity():
    """Test basic internet connectivity"""
    print("\n🌐 Testing Basic Internet Connectivity...")
    
    test_urls = [
        'https://google.com',
        'https://httpbin.org/get',
        'https://www.googleapis.com'
    ]
    
    connectivity_results = {}
    
    for url in test_urls:
        try:
            start_time = time.time()
            response = requests.get(url, timeout=10)
            end_time = time.time()
            
            connectivity_results[url] = {
                'status': '✅ Success',
                'status_code': response.status_code,
                'response_time': f"{(end_time - start_time):.2f}s"
            }
            print(f"  {url}: ✅ {response.status_code} ({(end_time - start_time):.2f}s)")
            
        except requests.exceptions.Timeout:
            connectivity_results[url] = {'status': '❌ Timeout', 'error': 'Request timed out'}
            print(f"  {url}: ❌ Timeout")
        except requests.exceptions.ConnectionError as e:
            connectivity_results[url] = {'status': '❌ Connection Error', 'error': str(e)}
            print(f"  {url}: ❌ Connection Error: {e}")
        except Exception as e:
            connectivity_results[url] = {'status': '❌ Error', 'error': str(e)}
            print(f"  {url}: ❌ Error: {e}")
    
    return connectivity_results

def test_google_oauth_endpoints():
    """Test specific Google OAuth endpoints"""
    print("\n🔐 Testing Google OAuth Endpoints...")
    
    endpoints = {
        'Discovery': 'https://accounts.google.com/.well-known/openid_configuration',
        'Authorization': 'https://accounts.google.com/o/oauth2/v2/auth',
        'Token': 'https://oauth2.googleapis.com/token',
        'UserInfo': 'https://www.googleapis.com/oauth2/v2/userinfo'
    }
    
    oauth_results = {}
    
    for name, url in endpoints.items():
        try:
            start_time = time.time()
            
            if name == 'Discovery':
                # For discovery, we expect JSON response
                response = requests.get(url, timeout=15)
                end_time = time.time()
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        oauth_results[name] = {
                            'status': '✅ Success',
                            'status_code': response.status_code,
                            'response_time': f"{(end_time - start_time):.2f}s",
                            'has_endpoints': bool(data.get('authorization_endpoint') and 
                                                 data.get('token_endpoint') and 
                                                 data.get('userinfo_endpoint'))
                        }
                        print(f"  {name}: ✅ {response.status_code} ({(end_time - start_time):.2f}s) - Valid JSON")
                    except json.JSONDecodeError:
                        oauth_results[name] = {
                            'status': '❌ Invalid JSON',
                            'status_code': response.status_code,
                            'response_time': f"{(end_time - start_time):.2f}s"
                        }
                        print(f"  {name}: ❌ {response.status_code} - Invalid JSON response")
                else:
                    oauth_results[name] = {
                        'status': f'❌ HTTP {response.status_code}',
                        'status_code': response.status_code,
                        'response_time': f"{(end_time - start_time):.2f}s"
                    }
                    print(f"  {name}: ❌ HTTP {response.status_code}")
            else:
                # For other endpoints, just check if they're reachable
                response = requests.head(url, timeout=10)
                end_time = time.time()
                
                oauth_results[name] = {
                    'status': '✅ Reachable' if response.status_code < 500 else f'❌ HTTP {response.status_code}',
                    'status_code': response.status_code,
                    'response_time': f"{(end_time - start_time):.2f}s"
                }
                print(f"  {name}: {'✅' if response.status_code < 500 else '❌'} {response.status_code} ({(end_time - start_time):.2f}s)")
                
        except requests.exceptions.Timeout:
            oauth_results[name] = {'status': '❌ Timeout', 'error': 'Request timed out'}
            print(f"  {name}: ❌ Timeout (>15s)")
        except requests.exceptions.ConnectionError as e:
            oauth_results[name] = {'status': '❌ Connection Error', 'error': str(e)}
            print(f"  {name}: ❌ Connection Error")
        except Exception as e:
            oauth_results[name] = {'status': '❌ Error', 'error': str(e)}
            print(f"  {name}: ❌ Error: {e}")
    
    return oauth_results

def test_with_different_user_agents():
    """Test with different User-Agent headers"""
    print("\n🤖 Testing with Different User Agents...")
    
    user_agents = {
        'Python Requests': 'python-requests/2.31.0',
        'Chrome': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Firefox': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
        'SilverSage App': 'SilverSage/1.0.0 Flask OAuth Client'
    }
    
    url = 'https://accounts.google.com/.well-known/openid_configuration'
    ua_results = {}
    
    for name, ua in user_agents.items():
        try:
            headers = {'User-Agent': ua}
            response = requests.get(url, headers=headers, timeout=10)
            
            ua_results[name] = {
                'status': '✅ Success' if response.status_code == 200 else f'❌ HTTP {response.status_code}',
                'status_code': response.status_code
            }
            print(f"  {name}: {'✅' if response.status_code == 200 else '❌'} {response.status_code}")
            
        except Exception as e:
            ua_results[name] = {'status': '❌ Error', 'error': str(e)}
            print(f"  {name}: ❌ Error: {e}")
    
    return ua_results

def check_proxy_settings():
    """Check if proxy settings might be interfering"""
    print("\n🔧 Checking Proxy Configuration...")
    
    import os
    
    proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'NO_PROXY', 'no_proxy']
    proxy_settings = {}
    
    for var in proxy_vars:
        value = os.environ.get(var)
        if value:
            proxy_settings[var] = value
            print(f"  {var}: {value}")
        else:
            proxy_settings[var] = None
    
    if not any(proxy_settings.values()):
        print("  ✅ No proxy environment variables detected")
    
    return proxy_settings

def generate_solutions(results):
    """Generate specific solutions based on test results"""
    print("\n" + "="*60)
    print("🔧 DIAGNOSTIC RESULTS & SOLUTIONS")
    print("="*60)
    
    dns_failed = any('❌' in str(result) for result in results['dns'].values())
    connectivity_failed = any(result.get('status', '').startswith('❌') for result in results['connectivity'].values())
    oauth_discovery_failed = results['oauth'].get('Discovery', {}).get('status', '').startswith('❌')
    
    if dns_failed:
        print("\n🚨 DNS RESOLUTION ISSUES DETECTED")
        print("Solutions:")
        print("1. Try changing DNS servers:")
        print("   - Google DNS: 8.8.8.8, 8.8.4.4")
        print("   - Cloudflare DNS: 1.1.1.1, 1.0.0.1")
        print("2. Flush DNS cache:")
        print("   - Windows: ipconfig /flushdns")
        print("   - macOS: sudo dscacheutil -flushcache")
        print("   - Linux: sudo systemd-resolve --flush-caches")
        print("3. Check if your ISP is blocking Google services")
        
    elif connectivity_failed:
        print("\n🚨 NETWORK CONNECTIVITY ISSUES DETECTED")
        print("Solutions:")
        print("1. Check your internet connection")
        print("2. Verify firewall settings aren't blocking outbound HTTPS")
        print("3. If on corporate network, contact IT about proxy settings")
        print("4. Try from a different network (mobile hotspot)")
        
    elif oauth_discovery_failed:
        print("\n🚨 GOOGLE OAUTH DISCOVERY ENDPOINT ISSUES")
        print("Solutions:")
        print("1. Google services might be temporarily down")
        print("2. Your IP might be rate-limited by Google")
        print("3. Try again in a few minutes")
        print("4. Check Google Workspace Status: https://www.google.com/appsstatus/dashboard/")
        
    else:
        print("\n✅ NETWORK CONNECTIVITY APPEARS NORMAL")
        print("The issue might be in your Flask application. Try:")
        print("1. Restart your Flask application")
        print("2. Check Flask logs for detailed error messages")
        print("3. Verify your .env file is in the correct location")
        print("4. Try the OAuth flow manually")

def main():
    print("🔍 SilverSage Google OAuth Network Diagnostic Tool")
    print("="*60)
    print("This tool will help diagnose network connectivity issues")
    print("that prevent Google OAuth from working properly.\n")
    
    try:
        # Run all tests
        results = {
            'dns': test_dns_resolution(),
            'connectivity': test_basic_connectivity(),
            'oauth': test_google_oauth_endpoints(),
            'user_agents': test_with_different_user_agents(),
            'proxy': check_proxy_settings()
        }
        
        # Generate solutions
        generate_solutions(results)
        
        print("\n" + "="*60)
        print("📊 SUMMARY")
        print("="*60)
        
        # DNS Summary
        dns_ok = all('✅' in str(result) for result in results['dns'].values())
        print(f"DNS Resolution: {'✅ Working' if dns_ok else '❌ Issues detected'}")
        
        # Connectivity Summary
        conn_ok = all(result.get('status', '').startswith('✅') for result in results['connectivity'].values())
        print(f"Basic Connectivity: {'✅ Working' if conn_ok else '❌ Issues detected'}")
        
        # OAuth Summary
        oauth_ok = results['oauth'].get('Discovery', {}).get('status', '').startswith('✅')
        print(f"Google OAuth Discovery: {'✅ Working' if oauth_ok else '❌ Failed'}")
        
        if dns_ok and conn_ok and oauth_ok:
            print("\n🎉 All network tests passed! The issue might be in your Flask configuration.")
            print("Try restarting your Flask app and check the application logs.")
        else:
            print(f"\n⚠️ Issues detected. Follow the solutions above to fix the problems.")
            
    except KeyboardInterrupt:
        print("\n\n👋 Diagnostic cancelled by user")
    except Exception as e:
        print(f"\n❌ Unexpected error during diagnosis: {e}")
        print("Please ensure you have the 'requests' package installed:")
        print("pip install requests")

if __name__ == "__main__":
    main()