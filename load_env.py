#!/usr/bin/env python3
"""
Environment Variable Loader

Simple utility to load environment variables from .env file
without requiring external dependencies like python-dotenv.
"""

import os


def load_env(env_file=".env"):
    """Load environment variables from a .env file."""
    if not os.path.exists(env_file):
        return False
    
    try:
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Parse KEY=VALUE format
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    
                    # Set environment variable
                    os.environ[key] = value
        
        return True
    
    except Exception as e:
        print(f"Error loading .env file: {e}")
        return False


if __name__ == "__main__":
    # Test the loader
    if load_env():
        print("✅ .env file loaded successfully")
        
        # Show loaded variables (without values for security)
        env_vars = ['DISCOGS_TOKEN', 'SPOTIFY_CLIENT_ID', 'SPOTIFY_CLIENT_SECRET']
        for var in env_vars:
            if var in os.environ:
                print(f"   {var}: {'*' * min(len(os.environ[var]), 20)}")
    else:
        print("⚠️  No .env file found or error loading it")
        print("   Create a .env file based on env.example")
