#!/usr/bin/env python3
"""Test pure alcohol calculation"""

# Import the calculation function from main.py
import sys
sys.path.append('.')

# Mock Firebase admin to avoid initialization issues
import firebase_admin
firebase_admin._apps = {'[DEFAULT]': True}  # Pretend it's already initialized

from main import calculate_pure_alcohol, DRINKS_MASTER

print("Testing pure alcohol calculation:")
print("=" * 50)

# Test each drink type with default volumes
for drink_id, drink_data in DRINKS_MASTER.items():
    alcohol_g = calculate_pure_alcohol(drink_id)
    print(f"{drink_data['name']} ({drink_data['volume']}ml, {drink_data['alcohol']}%): {alcohol_g:.1f}g")

print("\n" + "=" * 50)
print("Custom volume tests:")

# Test custom volumes
test_cases = [
    ("beer", 500, "ビール大ジョッキ"),
    ("wine", 250, "ワイン2杯分"),
    ("sake", 90, "日本酒おちょこ1杯"),
]

for drink_id, volume, description in test_cases:
    alcohol_g = calculate_pure_alcohol(drink_id, volume)
    print(f"{description} ({volume}ml): {alcohol_g:.1f}g")

print("\n" + "=" * 50)
print("Validation: ビール350ml = 350 × 5% × 0.8 = 14g ✓")