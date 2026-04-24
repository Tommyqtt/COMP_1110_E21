# Category Management Guide

## Quick Start: Add a Category in 3 Steps

### Terminal (CLI)
```
1. Start: python3 main.py
2. Press: c (Manage categories)
3. Press: 1 (Add a new category)
4. Type: gym (or any category name)
5. Result: ✓ Category 'gym' added successfully!
```

### GUI
1. Click the **Categories** tab
2. Type category name in the text field
3. Click **Add category** button
4. See instant feedback

---

## Terminal Guide - Detailed Steps

### Step 1: Open the CLI
```bash
python3 main.py
```

### Step 2: Navigate to Category Management
In the main menu:
```
Choice: c
```

### Step 3: Choose "Add a new category"
In the category menu:
```
Choice: 1
```

### Step 4: Enter Your Category Name
```
Enter new category name: healthcare
```

| Feature | Behavior |
|---------|----------|
| **Auto-save** | ✓ Saves immediately to `categories.txt` |
| **Duplicates** | ✗ Automatically rejected |
| **Case handling** | Converted to lowercase automatically |
| **Continue loop** | After adding, ask if you want to add more |

### Step 5: Add More or Return
```
Continue managing categories? (y/n): y
```
- **y** → Add another category
- **n** → Return to main menu

---

## Available Options in Category Management

```
--- Manage Categories ---
Current categories (5): food, transport, housing, entertainment, others

Options:
  1. Add a new category        ← Add custom categories
  2. View all categories       ← See your complete list with count
  3. Back to menu              ← Exit and return to main
```

---

## Usage Across the App

Once you add categories, they appear in:

| Feature | Where Used |
|---------|-----------|
| **Add Transaction** | Category dropdown |
| **Edit Transaction** | Category dropdown |
| **Budget Rules** | Category list |
| **Alerts** | Category thresholds |
| **Filters** | Transaction filtering |

---

## Storage & Persistence

- **File**: `categories.txt` (created in app directory)
- **Format**: One category per line (all lowercase)
- **Auto-create**: Defaults used if file doesn't exist
- **Automatic save**: Changes saved immediately after adding

**Example `categories.txt`:**
```
food
transport
housing
entertainment
others
gym
healthcare
insurance
```

---

## Example Categories to Try

### Financial
- `insurance`
- `taxes`
- `banking`
- `investments`

### Entertainment
- `gym`
- `movies`
- `gaming`
- `hobbies`

### Home & Life
- `healthcare`
- `medical`
- `childcare`
- `education`

### Utilities
- `utilities`
- `internet`
- `phone`
- `electricity`

### Travel
- `travel`
- `uber/taxi`
- `flights`
- `hotels`

### Lifestyle
- `dining`
- `restaurants`
- `coffee`
- `groceries`
- `shopping`
- `gifts`

---

## Tips & Tricks

✅ **Use descriptive names** - "gym_membership" vs "gym"  
✅ **Keep them short** - Easier to type and remember  
✅ **Grouping** - Similar categories together (e.g., "gym", "sports", "fitness")  
✅ **View all** - Use option 2 to see categories if you forget one  
✅ **No spaces** - Category names work best with underscores or hyphens  

---

## Validation Rules

| Rule | Result |
|------|--------|
| **Empty name** | Invalid - prompts to try again |
| **Already exists** | Rejected - "Category 'X' already exists" |
| **Duplicate attempt** | Caught - prevents duplicates |
| **Special characters** | Converted to lowercase automatically |
| **Spaces** | Allowed but converted to lowercase |

---

## Troubleshooting

**Q: Can I delete a category?**  
A: Not through the UI currently. Manually edit `categories.txt` or delete it to reset to defaults.

**Q: Can I rename a category?**  
A: No direct rename. Delete and add new one. Add the new category name, then reuse it in transactions.

**Q: Where are categories stored?**  
A: Check `categories.txt` in the app directory.

**Q: Can I see all my categories?**  
A: Yes! In Category Management menu → Choose option 2 "View all categories"

**Q: Do categories persist after restart?**  
A: Yes! Automatically saved to `categories.txt` and loaded on startup.

---

## For Developers

- Main function: `manage_categories()` in [main.py](main.py)
- Core logic: `add_category()` in [data.py](data.py)
- GUI tab: `create_categories_tab()` in [ui.py](ui.py)
- Storage: `categories.txt` (plain text, one per line)
