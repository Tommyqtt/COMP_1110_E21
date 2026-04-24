import os
from data import load_categories, add_category, CATEGORIES, CATEGORY_FILE

def test_unlimited_categories():
    print("--- Testing Unlimited Budget Categories ---")

    # Step 1: Clean up any existing test file to ensure a fresh start
    if os.path.exists(CATEGORY_FILE):
        os.remove(CATEGORY_FILE)
        print(f"1. Removed existing '{CATEGORY_FILE}' for a clean slate.")

    # Step 2: Load categories (should load the defaults since the file was deleted)
    load_categories()
    print(f"2. Initial categories loaded: {CATEGORIES}")

    # Step 3: Add new custom categories
    print("\n3. Adding new categories: 'healthcare' and 'education'...")
    add_category("healthcare")
    add_category("education")
    print(f"   Current memory state after addition: {CATEGORIES}")

    # Step 4: Simulate a program exit and restart
    print("\n4. Simulating program restart...")
    CATEGORIES.clear() # Wipe the in-memory list completely
    print(f"   Memory wiped. Current memory state: {CATEGORIES}")

    load_categories() # Reload from the text file
    print(f"   Categories reloaded from text file: {CATEGORIES}")

    # Step 5: Verify the results
    if "healthcare" in CATEGORIES and "education" in CATEGORIES:
        print("\n✅ TEST PASSED: The custom categories were successfully saved and reloaded!")
    else:
        print("\n❌ TEST FAILED: The custom categories were lost after the simulated restart.")

if __name__ == "__main__":
    test_unlimited_categories()