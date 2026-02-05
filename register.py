from playwright.sync_api import sync_playwright
import time
import sys
from data_manager import DataManager

def parse_geolocation(geo_str):
    """
    Parses string "lat, long" from CSV into {'latitude': float, 'longitude': float}
    Example input: "29.452137, -98.642559"
    """
    try:
        lat_str, lon_str = geo_str.split(',')
        return {
            'latitude': float(lat_str.strip()),
            'longitude': float(lon_str.strip())
        }
    except ValueError:
        print(f"Error parsing geolocation: {geo_str}. Using default.")
        return {'latitude': 29.450411, 'longitude': -98.644806}

def run_registration(register_page, email, password, geolocation, full_address, unit_number):
    with sync_playwright() as p:
        # Launch browser and configure mobile environment
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            permissions=['geolocation'],
            geolocation=geolocation,
            # viewport={'width': 390, 'height': 844},
            # is_mobile=True,
            # user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
        )
        page = context.new_page()

        try:
            print(f"Opening website: {register_page}")
            page.goto(register_page)
            print("Paused for debugging. Use Playwright Inspector to step through.")

            # ===== PAGE 1: Email & Password =====
            if "referral_id" in register_page:
                # Referral Flow: Wait for popup, then click "Continue" in the popup
                print("Referral link detected. Waiting for popup...")
                try:
                    # Wait for popup to appear by checking if there are 3 "Continue" elements
                    # Initial: "Continue with Google" + form "Continue" = 2
                    # After popup: "Continue with Google" + form "Continue" + popup "Continue" = 3
                    max_wait = 5  # seconds
                    for i in range(max_wait):
                        continue_buttons = page.get_by_text("Continue", exact=False).all()
                        if len(continue_buttons) >= 3:
                            print(f"Popup appeared! Found {len(continue_buttons)} Continue buttons")
                            break
                        time.sleep(1)
                    
                    # Click the last Continue button (the popup one)
                    page.get_by_text("Continue").last.click(timeout=5000)
                    print("Clicked popup Continue button")
                except Exception as e:
                    print(f"Popup handling failed: {e}, proceeding without clicking...")
            else:
                # Default Flow: Click "Sign up" then handle potential popup
                print("Default page detected. Clicking Sign up...")
                page.get_by_text("Sign up").click()
                
                # Handle welcome popup if it appears (only for default flow per observation, 
                # or maybe it's the same 'Continue' button but in a different order)
                try:
                    page.wait_for_selector("text=Howdy", timeout=5000)
                    page.get_by_text("Continue").last.click()
                except:
                    print("No welcome popup or timed out, continuing...")

            page.locator('input[type=\"email\"]').fill(email)
            page.locator('input[type=\"password\"]').fill(password)
            
            # Click the checkbox icon (not the text link)
            # The checkbox is in a div with specific styling, we target by its structure
            checkbox_selector = 'div.css-175oi2r.r-1ifxtd0 div.css-175oi2r.r-5oul0u.r-knv0ih div div.css-146c3p1.r-lrvibr'
            try:
                page.locator(checkbox_selector).click(timeout=5000)
                print("Clicked checkbox icon for agreement")
            except Exception as e:
                print(f"Failed to click checkbox with selector, trying alternative: {e}")
                # Fallback: Try clicking any unchecked checkbox-like element near "I agree"
                page.locator('div.r-5oul0u').first.click()
            
            page.get_by_text("Continue").last.click()
            print(f"Successfully passed credential page.")

            # ===== PAGE 2: Registration Details =====
            
            # Community/Property dropdown
            page.locator('input[placeholder="What Community / Property do you live in?"]').click()
            dropdown_menu = page.locator('div[style*="box-shadow"]')
            dropdown_menu.wait_for()
            dropdown_menu.locator('div[tabindex="0"]').first.click()
            
            # Address input
            page.get_by_placeholder("Enter full address (street number, street name, city, state, zip)").fill(full_address)

            # Unit number input
            page.get_by_placeholder("Enter unit number, if applicable").fill(unit_number)

            # Referral dropdown ("How did you hear about...")
            page.get_by_text("How did you hear about").last.click()
            referral_menu = page.locator('div[style*="box-shadow"]')
            referral_menu.wait_for()
            referral_menu.locator('div[dir="auto"]').first.click()

            # Submit registration
            print("Clicking Create Account...")
            page.get_by_text("Create an account").click()
            
            # Allow some time for submission to process
            time.sleep(3) 
            
            return True

        except Exception as e:
            print(f"Error during browser interaction: {e}")
            return False
        finally:
            browser.close()

def run_automated_registration(accounts_to_register, password):
    """
    Register accounts directly from an in-memory list.
    
    Args:
        accounts_to_register: List of dicts with keys: email, geolocation, full_address, unit_number, phone_number
        password: Password to use for all accounts
        
    Returns:
        int: Number of successfully registered accounts
    """
    dm = DataManager()
    successful = 0
    
    print(f"Attempting to register {len(accounts_to_register)} accounts...")

    for i, account_data in enumerate(accounts_to_register):
        print(f"\n--- Processing Account {i+1}/{len(accounts_to_register)} ---")
        
        # Extract data from in-memory dict
        email = account_data['email']
        candidate_name = email.split('@')[0]
        raw_geo = account_data['geolocation']
        full_address = account_data['full_address']
        unit_number = account_data['unit_number']
        phone_number = account_data['phone_number']

        # Check if already registered
        if dm.email_exists_in_data(email):
            print(f"Skipping {email}, already exists in account_data.csv.")
            continue

        uid = dm.generate_uid()
        
        # Parse Geolocation String
        geo_dict = parse_geolocation(raw_geo)

        # Decide whether to use referral
        use_referral = True 
        register_page, referrer_uid = dm.get_register_page(use_refer=use_referral, base_url="https://m.amenify.com")

        print(f"Starting registration for {candidate_name}...")
        print(f"Address: {full_address} (Unit {unit_number})")
        print(f"Geo: {geo_dict}")

        # Run Registration
        success = run_registration(
            register_page=register_page,
            email=email,
            password=password,
            geolocation=geo_dict,
            full_address=full_address,
            unit_number=unit_number
        )
        
        if success:
            print("Registration successful.")
            
            # Save to Output CSV (account_data.csv) immediately
            row_data = {
                "UID": uid,
                "register_page": register_page,
                "email": email,
                "password": password,
                "geolocation": str(geo_dict),
                "full_address": full_address,
                "unit_number": unit_number,
                "full_name": candidate_name.replace('.', ' ').replace('_', ' ').title(),
                "phone_number": phone_number,
                "refer_link": "",
                "refer_by": referrer_uid if referrer_uid else "",
                "refer_amount": "0",
                "card": "",
                "received_amount": "",
                "paid_amount": "",
                "unfull_filled": "",
                "remain_credit": ""
            }
            dm.save_row(row_data)
            successful += 1
            
            # Increment referral amount if applicable
            if referrer_uid:
                dm.increment_referral_amount(referrer_uid)
            
            print("Data saved to account_data.csv.")
            
            # Brief pause between accounts
            time.sleep(2)
        else:
            print("Registration failed. Skipping to next account...")
    
    print(f"\n=== Registration Complete: {successful}/{len(accounts_to_register)} successful ===")
    return successful

