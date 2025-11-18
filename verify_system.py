#!/usr/bin/env python3
"""
System Verification Test
Checks all components are working before live trading
"""

import sys
import os
from pathlib import Path

# Add to path
sys.path.append(str(Path(__file__).parent))

print("="*60)
print("🔍 HYPERAI TRADER - SYSTEM VERIFICATION")
print("="*60)
print()

# Test 1: Check Python version
print("1️⃣  Checking Python version...")
version = sys.version_info
if version.major == 3 and version.minor >= 9:
    print(f"   ✅ Python {version.major}.{version.minor}.{version.micro}")
else:
    print(f"   ⚠️  Python {version.major}.{version.minor} (recommend 3.9+)")
print()

# Test 2: Check dependencies
print("2️⃣  Checking dependencies...")
required = [
    ('hyperliquid', 'HyperLiquid SDK'),
    ('pandas', 'Pandas'),
    ('numpy', 'NumPy'),
    ('dotenv', 'python-dotenv'),
    ('yaml', 'PyYAML')
]

all_deps_ok = True
for module, name in required:
    try:
        __import__(module)
        print(f"   ✅ {name}")
    except ImportError:
        print(f"   ❌ {name} - Run: pip install -r requirements.txt")
        all_deps_ok = False
print()

# Test 3: Check configuration files
print("3️⃣  Checking configuration...")
config_files = [
    ('.env', 'Credentials'),
    ('config.yaml', 'Strategy config'),
]

all_config_ok = True
for file, desc in config_files:
    if Path(file).exists():
        print(f"   ✅ {desc} ({file})")
    else:
        print(f"   ❌ {desc} ({file}) missing")
        all_config_ok = False
print()

# Test 4: Check directory structure
print("4️⃣  Checking directory structure...")
required_dirs = [
    'app/hl',
    'app/strategies/rule_based',
    'data/trades',
    'data/model_dataset',
    'ml/training',
    'logs'
]

all_dirs_ok = True
for dir_path in required_dirs:
    if Path(dir_path).is_dir():
        print(f"   ✅ {dir_path}/")
    else:
        print(f"   ❌ {dir_path}/ missing")
        all_dirs_ok = False
print()

# Test 5: Check core modules
print("5️⃣  Checking core modules...")
modules_to_test = [
    ('app.hl.hl_client', 'HyperLiquid Client'),
    ('app.hl.hl_websocket', 'WebSocket Manager'),
    ('app.hl.hl_order_manager', 'Order Manager'),
    ('app.strategies.rule_based.scalping_2pct', 'Scalping Strategy'),
    ('app.risk.risk_engine', 'Risk Engine'),
    ('app.risk.kill_switch', 'Kill Switch'),
    ('app.risk.drawdown_monitor', 'Drawdown Monitor'),
]

all_modules_ok = True
for module_path, name in modules_to_test:
    try:
        __import__(module_path)
        print(f"   ✅ {name}")
    except Exception as e:
        print(f"   ❌ {name} - {str(e)[:50]}")
        all_modules_ok = False
print()

# Test 6: Check credentials
print("6️⃣  Checking credentials...")
if Path('.env').exists():
    from dotenv import load_dotenv
    load_dotenv()
    
    credentials = [
        ('API_SECRET', 'API Secret'),
        ('ACCOUNT_ADDRESS', 'Account Address'),
    ]
    
    all_creds_ok = True
    for key, name in credentials:
        value = os.getenv(key)
        if value and value != '0x0000000000000000000000000000000000000000':
            print(f"   ✅ {name}")
        else:
            print(f"   ❌ {name} - Configure in .env")
            all_creds_ok = False
else:
    print("   ❌ .env file missing")
    all_creds_ok = False
print()

# Test 7: Check ML pipeline
print("7️⃣  Checking ML pipeline...")
ml_modules = [
    ('ml.training.dataset_builder', 'Dataset Builder'),
    ('ml.training.feature_engineering', 'Feature Engineering'),
]

all_ml_ok = True
for module_path, name in ml_modules:
    try:
        __import__(module_path)
        print(f"   ✅ {name}")
    except Exception as e:
        print(f"   ❌ {name} - {str(e)[:50]}")
        all_ml_ok = False
print()

# Final Summary
print("="*60)
print("📊 VERIFICATION SUMMARY")
print("="*60)

all_ok = all([
    all_deps_ok,
    all_config_ok,
    all_dirs_ok,
    all_modules_ok,
    all_creds_ok,
    all_ml_ok
])

if all_ok:
    print("✅ ALL CHECKS PASSED")
    print()
    print("Ready to start trading!")
    print("Run: python app/bot.py")
    print("Or: ./start.sh")
else:
    print("❌ SOME CHECKS FAILED")
    print()
    print("Fix the issues above before starting the bot.")
    print()
    print("Common fixes:")
    print("  - Install dependencies: pip install -r requirements.txt")
    print("  - Configure credentials: edit .env file")
    print("  - Run setup: ./setup.sh")

print("="*60)
print()

sys.exit(0 if all_ok else 1)
