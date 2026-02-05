from playwright.sync_api import sync_playwright
import time

def run_purchase(amazon_url, page=None):
    """
    Entry point for making a purchase. 
    If page is provided, it uses that browser session.
    If page is None, it attempts to connect to an existing Chrome instance on port 9222.
    """
    if page:
        print("Using provided browser session...")
        _execute_purchase_logic(page, amazon_url)
    else:
        print("No session provided. Connecting to local browser via CDP...")
        with sync_playwright() as p:
            try:
                browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
                default_context = browser.contexts[0]
                page = default_context.pages[0]
                print("Successfully connected to your open browser.")
                
                _execute_purchase_logic(page, amazon_url)
                
            except Exception as e:
                print("Could not connect to browser. Make sure you ran the Chrome command in Step 1!")
                print(f"Error: {e}")
                return


def navigate_to_purchase_page(page):
    """
    Navigate from clean home page to the BYOP (Bring Your Own Product) popup.
    Stops BEFORE the URL input step - user will paste URL manually.
    
    Args:
        page: Playwright page object at a clean home page
        
    Returns:
        page: The page object at the BYOP popup, ready for manual URL input
    """
    print("Navigating to purchase page...")
    
    # --- Click "ACommerce" ---
    print("Step 1: Clicking ACommerce...")
    try:
        page.get_by_text("ACommerce").first.click()
    except Exception as e:
        print(f"Error clicking ACommerce: {e}")
        raise

    print("Step 2: Waiting for the ACommerce Iframe to load...")
    
    # 1. DEFINE THE IFRAME
    shop_frame = page.frame_locator("iframe[src*='acommerce']")
    
    # 2. Wait for the content INSIDE the iframe to exist
    header_inside_frame = shop_frame.locator("text=Shop for Home Products")
    try:
        header_inside_frame.wait_for(timeout=15000)
        print("Iframe loaded successfully!")
    except:
        print("Warning: Iframe took too long, trying to proceed anyway...")

    # 3. SCROLL THE DIV INSIDE THE IFRAME
    print("Step 3: Scrolling the iframe content...")
    try:
        scrollable_box = shop_frame.locator("div.shadow-box").first
        scrollable_box.evaluate("el => el.scrollTop = el.scrollHeight")
        time.sleep(1) 
    except Exception:
        print("Could not scroll iframe (might vary by screen size/state).")

    # 4. CLICK THE BUTTON
    print("Step 4: Clicking 'Amazon Products' inside the iframe...")
    try:
        amazon_btn = shop_frame.locator('a[onclick*="show_byop_modal"]')
        amazon_btn.click(force=True)
        print("Success! BYOP modal opened.")
    except Exception as e:
        print(f"Error clicking Amazon Products button: {e}")
        raise
    
    time.sleep(1)
    
    print("✅ Ready for manual purchase. Please paste product URL and complete purchase.")
    return page


def _execute_purchase_logic(page, amazon_url):
    """
    Internal function containing the core automation logic.
    """
    
    # --- Click "ACommerce" ---
    print("Navigating to ACommerce...")
    try:
        page.get_by_text("ACommerce").first.click()
    except Exception as e:
        print(f"Error clicking ACommerce: {e}")
        # Assuming we might already be there or it failed, but continuing...

    print("Waiting for the ACommerce Iframe to load...")
    
    # 1. DEFINE THE IFRAME
    shop_frame = page.frame_locator("iframe[src*='acommerce']")
    
    # 2. Wait for the content INSIDE the iframe to exist
    header_inside_frame = shop_frame.locator("text=Shop for Home Products")
    try:
        header_inside_frame.wait_for(timeout=15000)
        print("Iframe loaded successfully!")
    except:
        print("Warning: Iframe took too long, trying to proceed anyway...")

    # 3. SCROLL THE DIV INSIDE THE IFRAME
    print("Scrolling the iframe content...")
    try:
        scrollable_box = shop_frame.locator("div.shadow-box").first
        scrollable_box.evaluate("el => el.scrollTop = el.scrollHeight")
        time.sleep(1) 
    except Exception:
        print("Could not scroll iframe (might vary by screen size/state).")

    # 4. CLICK THE BUTTON
    print("Clicking 'Amazon Products' inside the iframe...")
    try:
        amazon_btn = shop_frame.locator('a[onclick*="show_byop_modal"]')
        amazon_btn.click(force=True)
        print("Success! Button clicked.")
    except Exception as e:
        print(f"Error clicking Amazon Products button: {e}")

    # --- Handle "Bring Your Own Product" Popup ---
    print("Entering product URL...")
   
    # 1. Use the parameterized URL
    target_url = amazon_url

    # 2. Fill the Input Field
    shop_frame.locator("#byop-product-url").fill(target_url)

    # 3. Click Submit
    shop_frame.get_by_role("button", name="Submit").click()

    # --- Wait for Fetching (Max 2 Minutes) ---
    print("Fetching product details (Timeout: 2 mins)...")

    try:
        buy_now_btn = shop_frame.locator(".amazon-buy-now-btn")
        buy_now_btn.wait_for(timeout=120000)
        buy_now_btn.click()
        print("Successfully clicked 'Buy Now'.")

    except Exception as e:
        print("ERROR: Timed out waiting for product details (fetched longer than 2 mins).")
        raise e 

    # --- Final Step: Price Check & Purchase Decision ---
    print("Checking 'Amount to pay'...")

    # 1. Locate and Extract the Price
    price_row = shop_frame.locator("div.flex.justify-between", has_text="Amount to pay:")
    price_row.wait_for()
    
    raw_price_text = price_row.locator("b").inner_text()
    print(f"Raw price detected: {raw_price_text}")

    # 2. Clean and Parse the Data
    try:
        price_value = float(raw_price_text.replace("$", "").replace(",", ""))
    except ValueError:
        print("Error: Could not parse price. Safety Cancel initiated.")
        price_value = 999.00 

    # 3. The Logic ( < $5.00 )
    if price_value < 5.00:
        print(f"Price (${price_value}) is acceptable. Buying Gift Card...")
        shop_frame.get_by_role("button", name="Buy Amazon Gift Card").click()
    else:
        print(f"Price (${price_value}) is too high. Canceling...")
        shop_frame.get_by_role("button", name="Cancel").click()
    
    # --- Final Verification: Order Success ---
    print("Waiting for order confirmation (Timeout: 2 mins)...")

    try:
        success_btn = shop_frame.get_by_role("button", name="View Order Status")
        success_btn.wait_for(timeout=120000)
        success_btn.click()
        print("SUCCESS: Amazon Order Placed! 'View Order Status' clicked.")
        print("Script finished. Browser left open.")

    except Exception:
        print("CRITICAL FAILURE: Did not receive confirmation.")