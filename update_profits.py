
import json
import os
from pathlib import Path

CONFIG_PATH = r"c:\Users\Student\Documents\GitHub\albion_market_main\config\coordinates.json"

def calculate_min_profit(tier, enchant):
    # Rule 1: Enchants
    if enchant > 0:
        if 4 <= tier <= 6:
            return 20
        elif 7 <= tier <= 8:
            return 10
        return 15 # Default/Fallback
    
    # Rule 2: Flat (Enchant 0)
    if tier == 4: return 35
    if tier == 5: return 25
    if tier == 6: return 20
    if tier >= 7: return 15
    
    return 15 # Fallback

def main():
    if not os.path.exists(CONFIG_PATH):
        print(f"File not found: {CONFIG_PATH}")
        return

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "wholesale_targets" not in data:
        print("No 'wholesale_targets' found in config.")
        return

    targets = data["wholesale_targets"]
    count = 0
    
    for item_name, variants in targets.items():
        for key, details in variants.items():
            # Parse Key "T4.0"
            try:
                tier_str, enchant_str = key.replace("T", "").split(".")
                tier = int(tier_str)
                enchant = int(enchant_str)
                
                new_profit = calculate_min_profit(tier, enchant)
                
                if details.get("min_profit") != new_profit:
                    print(f"Updating {item_name} {key}: {details.get('min_profit')} -> {new_profit}%")
                    details["min_profit"] = new_profit
                    count += 1
            except Exception as e:
                print(f"Error parsing key {key}: {e}")

    if count > 0:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"✅ Updated {count} entries.")
    else:
        print("No changes needed.")

if __name__ == "__main__":
    main()
