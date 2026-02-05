from playwright.sync_api import sync_playwright
import time
import csv
import os

def run_update_credits(email, page):
    """
    Updates the wallet credits for a specific account.
    Receives a clean home page (usually after signin), checks the "wallet credits" balance,
    and updates the balance in the CSV file.
    
    Args:
        email: User email to identify the account in CSV
        page: Playwright page object (should be on a clean home page)
    
    Returns:
        float: The credit balance (e.g., 12.50 for $12.50)
    """
    print(f"Checking wallet credits for {email}...")
    time.sleep(2)
    
    # Extract wallet credit from the page
    try:
        # Look for the element containing the credit amount
        # It follows the pattern ": $0" or ": $12.50" etc.
        credit_elements = page.locator('div[dir="auto"][style*="font-family: avenir-next-demi-bold"]')
        
        # Find the element that contains ": $"
        credit_value = None
        for i in range(credit_elements.count()):
            text = credit_elements.nth(i).inner_text()
            if text.startswith(": $"):
                # Extract the number after ": $"
                credit_str = text.replace(": $", "").strip()
                credit_value = float(credit_str)
                print(f"Found wallet credit: ${credit_value}")
                break
        
        if credit_value is None:
            print("Warning: Could not find wallet credit element. Trying alternative method...")
            # Alternative: look for text containing "Wallet credits" and find nearby amount
            wallet_label = page.locator('div[dir="auto"]', has_text="Wallet credits")
            if wallet_label.is_visible(timeout=3000):
                # The credit amount is usually a sibling or nearby element
                parent = wallet_label.locator('..')
                amount_elements = parent.locator('div[dir="auto"]')
                for i in range(amount_elements.count()):
                    text = amount_elements.nth(i).inner_text()
                    if ": $" in text:
                        credit_str = text.replace(": $", "").strip()
                        credit_value = float(credit_str)
                        print(f"Found wallet credit (alternative method): ${credit_value}")
                        break
        
        if credit_value is None:
            raise Exception("Could not locate wallet credit value on page")
            
    except Exception as e:
        print(f"Error extracting wallet credits: {e}")
        print("Returning 0 as fallback")
        credit_value = 0.0
    
    # Update the CSV file
    _update_credit_in_csv(email, credit_value)
    
    return credit_value


def _update_credit_in_csv(email, credit_value):
    """
    Updates the remain_credit column for the account with the given email.
    """
    csv_file = "account_data.csv"
    
    if not os.path.exists(csv_file):
        print(f"Error: {csv_file} not found")
        return
    
    rows = []
    updated = False
    
    # Read all rows
    with open(csv_file, mode='r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)
    
    # Update the specific row
    for row in rows:
        if row.get('email') == email:
            row['remain_credit'] = str(credit_value)
            updated = True
            print(f"Updated {email}: remain_credit = ${credit_value}")
            break
    
    # Write back if updated
    if updated:
        with open(csv_file, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"CSV updated successfully for {email}")
    else:
        print(f"Warning: Email {email} not found in {csv_file}")
