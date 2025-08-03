#!/usr/bin/env python3
"""
Quick Network Test for Google OAuth Discovery Issue
Run this to quickly test if you can reach Google's services
"""

import requests
import time

def quick_test():
    """Quick test to diagnose the Google Discovery failure"""
    print("🔍 Quick Google OAuth Network Test")
    print("=" * 50)
    
    tests = [
        ("Basic Internet", "https://httpbin.org/get"),
        ("Google Main", "https://google.com"),
        ("Google APIs", "https://www.googleapis.com"),
        ("OAuth Discovery", "https://accounts.google.com/.well-known/openid_configuration")
    ]
    
    results = {}
    
    for name, url in tests:
        print(f"\nTesting {name}...")
        try:
            start_time = time.time()
            response = requests.get(url, timeout=10)
            end_time = time.time()
            
            if response.status_code == 200:
                results[name] = f"✅ Success ({response.status_code}) - {end_time - start_time:.2f}s"
                print(f"  ✅ {response.status_code} - {end_time - start_time:.2f}s")
            else:
                results[name] = f"⚠️ HTTP {response.status_code} - {end_time - start_time:.2f}s"
                print(f"  ⚠️ HTTP {response.status_code}")
                
        except requests.exceptions.Timeout:
            results[name] = "❌ Timeout (>10s)"
            print("  ❌ Timeout (>10 seconds)")
        except requests.exceptions.ConnectionError:
            results[name] = "❌ Connection Error"
            print("  ❌ Connection Error")
        except Exception as e:
            results[name] = f"❌ Error: {str(e)}"
            print(f"  ❌ Error: {e}")
    
    print("\n" + "=" * 50)
    print("📊 SUMMARY")
    print("=" * 50)
    
    for name, result in results.items():
        print(f"{name}: {result}")
    
    # Determine the issue
    oauth_failed = "❌" in results.get("OAuth Discovery", "")
    google_main_failed = "❌" in results.get("Google Main", "")
    basic_failed = "❌" in results.get("Basic Internet", "")
    
    print("\n🔧 DIAGNOSIS:")
    if basic_failed:
        print("❌ No internet connection or severe network issues")
        print("💡 Fix: Check your internet connection")
    elif google_main_failed:
        print("❌ Cannot reach Google services")
        print("💡 Fix: Google may be blocked by your network/firewall")
        print("💡 Try: Different network (mobile hotspot) or contact IT")
    elif oauth_failed:
        print("❌ Google OAuth discovery endpoint blocked")
        print("💡 Fix: Your network may be filtering specific Google APIs")
        print("💡 Try: VPN or different network")
    else:
        print("✅ All tests passed! Network connectivity is fine")
        print("💡 The issue may be in your Flask application configuration")
        print("💡 Try: Restart Flask app, check .env file location")

if __name__ == "__main__":
    try:
        quick_test()
    except KeyboardInterrupt:
        print("\n\n👋 Test cancelled")
    except ImportError:
        print("❌ Error: 'requests' package not installed")
        print("💡 Install with: pip install requests")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")