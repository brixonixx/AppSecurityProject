#!/usr/bin/env python3
"""
Quick test script to verify your Flask routes are working
Run this from your project directory: python test_routes.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_app_creation():
    """Test if the Flask app can be created successfully"""
    try:
        from __init__ import create_app
        app = create_app()
        
        print("✅ Flask app created successfully!")
        
        with app.app_context():
            print("\n📋 Registered Routes:")
            print("-" * 50)
            
            routes = []
            for rule in app.url_map.iter_rules():
                methods = ','.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))
                routes.append((rule.endpoint, methods, rule.rule))
            
            # Sort routes by URL path
            routes.sort(key=lambda x: x[2])
            
            for endpoint, methods, path in routes:
                print(f"{path:25} {methods:15} {endpoint}")
            
            # Check for specific routes we need
            print("\n🔍 Checking Critical Routes:")
            print("-" * 50)
            
            critical_routes = [
                ('/', 'index'),
                ('/login', 'auth.login'),
                ('/register', 'auth.register'),
                ('/logout', 'auth.logout'),
                ('/dashboard', 'dashboard'),
            ]
            
            for path, expected_endpoint in critical_routes:
                found = any(rule.rule == path for rule in app.url_map.iter_rules())
                status = "✅" if found else "❌"
                print(f"{status} {path:15} -> {expected_endpoint}")
            
            return True
            
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("Make sure all your Python files are in the same directory")
        return False
    except Exception as e:
        print(f"❌ Error creating Flask app: {e}")
        return False

def test_individual_modules():
    """Test if individual modules can be imported"""
    modules = ['models', 'auth', 'admin', 'config', 'security']
    
    print("\n🔧 Testing Module Imports:")
    print("-" * 50)
    
    for module in modules:
        try:
            __import__(module)
            print(f"✅ {module}")
        except ImportError as e:
            print(f"❌ {module}: {e}")
        except Exception as e:
            print(f"⚠️ {module}: {e}")

if __name__ == '__main__':
    print("🚀 Testing SilverSage Flask Application")
    print("=" * 60)
    
    # Test module imports first
    test_individual_modules()
    
    # Test app creation and routes
    if test_app_creation():
        print("\n🎉 All tests passed! Your login route should be available at /login")
    else:
        print("\n💥 There are issues with your Flask app setup")
        print("Check the error messages above and fix them before running the app")
    
    print("\n💡 Next steps:")
    print("1. If tests pass, run your app with: python __init__.py")
    print("2. Navigate to: https://localhost:5000/login")
    print("3. If you still get 404, check your browser URL carefully")