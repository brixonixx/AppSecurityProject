#!/usr/bin/env python3
"""
Google OAuth Configuration Checker for SilverSage
Run this script to diagnose Google OAuth configuration issues
"""

import os
import sys
import requests
from pathlib import Path
from dotenv import load_dotenv

def load_environment():
    """Load environment variables from .env file"""
    # Try to find .env file
    possible_paths = [
        Path('.env'),
        Path(__file__).parent / '.env',
        Path.cwd() / '.env'
    ]
    
    env_loaded = False
    env_path = None
    
    for path in possible_paths:
        if path.exists():
            load_dotenv(path)
            env_loaded = True
            env_path = path
            break
    
    return env_loaded, env_path

def check_google_discovery():
    """Check if Google's discovery endpoint is accessible"""
    try:
        response = requests.get(
            "https://accounts.google.com/.well-known/openid_configuration",
            timeout=10
        )
        response.raise_for_status()
        config = response.json()
        return True, config
    except Exception as e:
        return False, str(e)

def validate_client_id(client_id):
    """Validate Google Client ID format"""
    if not client_id:
        return False, "Client ID is empty"
    
    if not client_id.endswith('.apps.googleusercontent.com'):
        return False, "Client ID should end with '.apps.googleusercontent.com'"
    
    if len(client_id) < 50:
        return False, "Client ID appears too short"
    
    return True, "Valid format"

def validate_client_secret(client_secret):
    """Validate Google Client Secret format"""
    if not client_secret:
        return False, "Client Secret is empty"
    
    if len(client_secret) < 20:
        return False, "Client Secret appears too short"
    
    if not client_secret.startswith('GOCSPX-'):
        return False, "Client Secret should start with 'GOCSPX-'"
    
    return True, "Valid format"

def main():
    print("🔧 SilverSage Google OAuth Configuration Checker")
    print("=" * 60)
    
    # Step 1: Check .env file
    print("\n1. Checking .env file...")
    env_loaded, env_path = load_environment()
    
    if env_loaded:
        print(f"✅ Found .env file: {env_path}")
    else:
        print("❌ Could not find .env file")
        print("💡 Create a .env file in your project directory with:")
        print("   GOOGLE_CLIENT_ID=your-client-id")
        print("   GOOGLE_CLIENT_SECRET=your-client-secret")
        return
    
    # Step 2: Check environment variables
    print("\n2. Checking environment variables...")
    client_id = os.environ.get('GOOGLE_CLIENT_ID')
    client_secret = os.environ.get('GOOGLE_CLIENT_SECRET')
    
    print(f"GOOGLE_CLIENT_ID: {'✅ Set' if client_id else '❌ Not set'}")
    print(f"GOOGLE_CLIENT_SECRET: {'✅ Set' if client_secret else '❌ Not set'}")
    
    if not client_id or not client_secret:
        print("\n❌ Missing Google OAuth credentials!")
        print("💡 Please add them to your .env file:")
        print("   GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com")
        print("   GOOGLE_CLIENT_SECRET=GOCSPX-your-client-secret")
        return
    
    # Step 3: Validate credentials format
    print("\n3. Validating credentials format...")
    
    client_id_valid, client_id_msg = validate_client_id(client_id)
    print(f"Client ID format: {'✅' if client_id_valid else '❌'} {client_id_msg}")
    if client_id_valid:
        print(f"  Preview: {client_id[:30]}...")
    
    client_secret_valid, client_secret_msg = validate_client_secret(client_secret)
    print(f"Client Secret format: {'✅' if client_secret_valid else '❌'} {client_secret_msg}")
    
    # Step 4: Test Google connectivity
    print("\n4. Testing Google OAuth service connectivity...")
    discovery_ok, discovery_result = check_google_discovery()
    
    if discovery_ok:
        print("✅ Google OAuth discovery endpoint accessible")
        endpoints = discovery_result
        print(f"  Authorization: {endpoints.get('authorization_endpoint', 'Missing')}")
        print(f"  Token: {endpoints.get('token_endpoint', 'Missing')}")
        print(f"  UserInfo: {endpoints.get('userinfo_endpoint', 'Missing')}")
    else:
        print(f"❌ Cannot reach Google OAuth service: {discovery_result}")
        print("💡 Check your internet connection")
    
    # Step 5: Summary and recommendations
    print("\n5. Summary and Recommendations")
    print("=" * 60)
    
    all_good = env_loaded and client_id and client_secret and client_id_valid and client_secret_valid and discovery_ok
    
    if all_good:
        print("🎉 All checks passed! Your Google OAuth should work.")
        print("\n✅ Next steps:")
        print("1. Restart your Flask application")
        print("2. Visit http://localhost:5000/auth/google/debug")
        print("3. Try logging in with Google")
    else:
        print("❌ Issues found that need to be fixed:")
        
        if not env_loaded:
            print("- Create .env file with Google credentials")
        if not client_id:
            print("- Add GOOGLE_CLIENT_ID to .env file")
        if not client_secret:
            print("- Add GOOGLE_CLIENT_SECRET to .env file")
        if client_id and not client_id_valid:
            print("- Fix GOOGLE_CLIENT_ID format")
        if client_secret and not client_secret_valid:
            print("- Fix GOOGLE_CLIENT_SECRET format")
        if not discovery_ok:
            print("- Check internet connection")
        
        print("\n💡 For help getting Google credentials:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create project or select existing")
        print("3. Enable Google+ API")
        print("4. Create OAuth 2.0 credentials")
        print("5. Add redirect URI: http://localhost:5000/auth/google/callback")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Configuration check cancelled by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        print("💡 Please ensure you have the 'requests' and 'python-dotenv' packages installed:")
        print("   pip install requests python-dotenv")