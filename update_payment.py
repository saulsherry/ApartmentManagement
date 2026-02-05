from playwright.sync_api import sync_playwright
import time

def run_update_payment(card_num, expire_date, cvv, page=None):
    """
    Entry point for update payment method.
    If page is provided, it uses that browser session.
    If page is None, it attempts to connect to an existing Chrome instance on port 9222.
    
    Returns:
        page: The page object at a clean home page for further use.
    """
    if page:
        print("Using provided browser session...")
        return _execute_update_payment_logic(card_num, expire_date, cvv, page)
    else:
        print("No session provided. Connecting to local browser via CDP...")
        with sync_playwright() as p:
            try:
                browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
                default_context = browser.contexts[0]
                page = default_context.pages[0]
                print("Successfully connected to your open browser.")
                
                _execute_update_payment_logic(card_num,expire_date,cvv,page)
                
            except Exception as e:
                print("Could not connect to browser. Make sure you ran the Chrome command in Step 1!")
                print(f"Error: {e}")
                return


def navigate_to_payment_page(page):
    """
    Navigate from clean home page to the payment input page.
    Stops at the page where the user can manually input credit card details.
    
    Args:
        page: Playwright page object at a clean home page
        
    Returns:
        page: The page object at the payment input screen
    """
    print("Navigating to payment page...")
    time.sleep(1)
    
    # Step 1: Click on the settings icon at the bottom right corner
    print("Step 1: Clicking settings icon...")
    try:
        settings_btn = page.locator('button[role="button"] div[style*="font-family: material-community"][style*="font-size: 32px"]').last
        settings_btn.wait_for(timeout=5000)
        settings_btn.click()
        print("Settings icon clicked.")
    except Exception as e:
        print(f"Error clicking settings icon: {e}")
        raise
    
    time.sleep(2)
    
    # Step 2: Click on "Payment" text
    print("Step 2: Clicking Payment option...")
    try:
        payment_div = page.locator('div[tabindex="0"]:has-text("Payment")').first
        payment_div.wait_for(timeout=5000)
        payment_div.click()
        print("Payment option clicked.")
    except Exception as e:
        print(f"Error clicking Payment: {e}")
        raise
    
    time.sleep(2)
    
    # Step 3: Click on the pencil/edit icon next to "Add Card Details"
    print("Step 3: Clicking edit icon...")
    try:
        pencil_icon = page.locator('div.r-1loqt21[style*="font-family: material-community"][style*="font-size: 20px"]').first
        pencil_icon.wait_for(timeout=5000, state='visible')
        pencil_icon.click()
        print("Edit icon clicked.")
    except Exception as e:
        print(f"Error clicking edit icon: {e}")
        raise
    
    time.sleep(2)
    
    print("✅ Payment input page ready. Please manually enter credit card details.")
    return page


def _execute_update_payment_logic(card_num, expire_date, cvv, page):
    """
    Internal function containing the core automation logic.
    Starts from a clear home page, updates payment info, and returns to home page.
    
    Returns:
        page: The page object at a clean home page for further use.
    """
    import random
    import string
    
    # Generate random 9 character name for card
    random_name = ''.join(random.choices(string.ascii_uppercase, k=9))
    
    print("Starting payment update process...")
    time.sleep(2)
    
    # Step 1: Click on the settings icon at the bottom right corner
    print("Step 1: Clicking settings icon...")
    try:
        # Look for the settings button with material-community font icon
        settings_btn = page.locator('button[role="button"] div[style*="font-family: material-community"][style*="font-size: 32px"]').last
        settings_btn.wait_for(timeout=5000)
        settings_btn.click()
        print("Settings icon clicked.")
    except Exception as e:
        print(f"Error clicking settings icon: {e}")
        raise
    
    time.sleep(2)
    
    # Step 2: Click on "Payment" text
    print("Step 2: Clicking Payment option...")
    try:
        # The Payment text is inside a div that's being intercepted
        # We need to click the parent clickable element (tabindex="0")
        # Find the div containing "Payment" text and click its parent
        payment_div = page.locator('div[tabindex="0"]:has-text("Payment")').first
        payment_div.wait_for(timeout=5000)
        payment_div.click()
        print("Payment option clicked.")
    except Exception as e:
        print(f"Error clicking Payment: {e}")
        raise
    
    time.sleep(2)
    
    # Step 3: Click on the pencil/edit icon next to "Add Card Details"
    print("Step 3: Clicking edit icon...")
    try:
        # Target the actual clickable pencil icon element
        # It has class r-1loqt21 (which makes it hoverable/clickable - cursor: pointer)
        # and uses material-community font family
        # We need to find this specific icon within the payment section
        pencil_icon = page.locator('div.r-1loqt21[style*="font-family: material-community"][style*="font-size: 20px"]').first
        pencil_icon.wait_for(timeout=5000, state='visible')
        pencil_icon.click()
        print("Edit icon clicked.")
    except Exception as e:
        print(f"Error clicking edit icon: {e}")
        raise
    
    time.sleep(2)
    
    # Step 4: Fill in the card details
    print("Step 4: Filling card details...")
    try:
        # Get all text input fields
        input_fields = page.locator('input[data-testid="text-input-flat"]').all()
        
        if len(input_fields) >= 4:
            # Name on card (first input)
            input_fields[0].fill(random_name)
            print(f"Filled name: {random_name}")
            time.sleep(1)
            
            # Card number (second input - has autocomplete="cc-number")
            card_input = page.locator('input[autocomplete="cc-number"]')
            card_input.fill(card_num)
            print(f"Filled card number: {card_num[:4]}****")
            time.sleep(1)
            
            # Expiry date (third input - has autocomplete="cc-exp")
            expiry_input = page.locator('input[autocomplete="cc-exp"]')
            expiry_input.fill(expire_date)
            print(f"Filled expiry: {expire_date}")
            time.sleep(1)
            
            # CVV/CVC (fourth input - has autocomplete="cc-csc")
            cvv_input = page.locator('input[autocomplete="cc-csc"]')
            cvv_input.fill(cvv)
            print("Filled CVV: ***")
            time.sleep(1)
        else:
            # Fallback: use autocomplete selectors directly
            page.locator('input[data-testid="text-input-flat"]').first.fill(random_name)
            page.locator('input[autocomplete="cc-number"]').fill(card_num)
            page.locator('input[autocomplete="cc-exp"]').fill(expire_date)
            page.locator('input[autocomplete="cc-csc"]').fill(cvv)
            print("Card details filled using fallback method.")
            
    except Exception as e:
        print(f"Error filling card details: {e}")
        raise
    
    time.sleep(2)
    
    # Step 5: Click "Add Card" button
    print("Step 5: Clicking Add Card button...")
    try:
        add_card_btn = page.get_by_text("Add Card", exact=True)
        add_card_btn.wait_for(timeout=5000)
        add_card_btn.click()
        print("Add Card button clicked.")
    except Exception as e:
        print(f"Error clicking Add Card: {e}")
        raise
    
    # Step 6: Wait for 3-4 seconds for the card to be processed
    print("Step 6: Waiting for card processing...")
    time.sleep(4)
    
    # Step 7: Click on the home button to return to home page
    print("Step 7: Clicking Home button...")
    try:
        # The home button is typically the first button in the bottom navigation bar
        # Look for the home icon in the navigation
        home_btn = page.locator('button[role="button"] div[style*="font-family: material-community"][style*="font-size: 32px"]').first
        home_btn.wait_for(timeout=5000)
        home_btn.click()
        print("Home button clicked.")
    except Exception as e:
        print(f"Error clicking home button: {e}")
        # Alternative: try clicking a different home element
        try:
            # Try using navigation buttons - home is usually first
            nav_buttons = page.locator('button[role="button"]').all()
            if len(nav_buttons) > 0:
                nav_buttons[0].click()
                print("Home button clicked via alternative method.")
        except Exception as e2:
            print(f"Alternative home click also failed: {e2}")
            raise
    
    time.sleep(3)
    
    print("Payment update complete. Returning clean home page.")
    return page

# ... (your existing code)
