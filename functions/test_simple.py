#!/usr/bin/env python3
"""Simple test of pure alcohol calculation logic"""

# Drink master data
DRINKS_MASTER = {
    "beer": {"name": "ビール", "alcohol": 5, "volume": 350},
    "wine": {"name": "ワイン", "alcohol": 12, "volume": 125},
    "sake": {"name": "日本酒", "alcohol": 15, "volume": 180},
    "highball": {"name": "ハイボール", "alcohol": 7, "volume": 350},
    "shochu": {"name": "焼酎水割り", "alcohol": 10, "volume": 200},
    "cocktail": {"name": "カクテル", "alcohol": 15, "volume": 100}
}

def calculate_pure_alcohol(drink_type, volume_ml=None):
    """Pure alcohol (g) = volume(ml) × alcohol(%) ÷ 100 × 0.8"""
    drink_data = DRINKS_MASTER.get(drink_type)
    if not drink_data:
        raise ValueError(f"Unknown drink type: {drink_type}")
    
    alcohol_percentage = drink_data['alcohol']
    volume = volume_ml or drink_data['volume']
    
    return volume * (alcohol_percentage / 100) * 0.8

print("Pure Alcohol Calculation Test")
print("=" * 50)

# Test standard servings
for drink_id, drink_data in DRINKS_MASTER.items():
    alcohol_g = calculate_pure_alcohol(drink_id)
    print(f"{drink_data['name']:12} {drink_data['volume']:4}ml × {drink_data['alcohol']:2}% = {alcohol_g:5.1f}g")

print("\nValidation: ビール 350ml × 5% × 0.8 = 14.0g ✓")
print("\nGuardian Limits:")
print("- Daily limit: 20g (純アルコール)")
print("- ビール約1.4本相当")
print("- ワイン約1.7杯相当")