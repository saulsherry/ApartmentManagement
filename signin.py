from playwright.sync_api import sync_playwright
import time
import random


def _generate_valid_phone_number():
    """
    Generate a random valid US phone number.
    Uses valid US area codes and proper formatting.
    """
    # List of valid US area codes (common ones)
    valid_area_codes = [
        "201", "202", "203", "205", "206", "207", "208", "209", "210",
        "212", "213", "214", "215", "216", "217", "218", "219", "224",
        "225", "228", "229", "231", "234", "239", "240", "248", "251",
        "252", "253", "254", "256", "260", "262", "267", "269", "270",
        "272", "276", "281", "301", "302", "303", "304", "305", "307",
        "308", "309", "310", "312", "313", "314", "315", "316", "317",
        "318", "319", "320", "321", "323", "325", "330", "331", "334",
        "336", "337", "339", "347", "351", "352", "360", "361", "385",
        "386", "401", "402", "404", "405", "406", "407", "408", "409",
        "410", "412", "413", "414", "415", "417", "419", "423", "424",
        "425", "430", "432", "434", "435", "440", "442", "443", "469",
        "470", "475", "478", "479", "480", "484", "501", "502", "503",
        "504", "505", "507", "508", "509", "510", "512", "513", "515",
        "516", "517", "518", "520", "530", "531", "534", "539", "540",
        "541", "551", "559", "561", "562", "563", "567", "570", "571",
        "573", "574", "575", "580", "585", "586", "601", "602", "603",
        "605", "606", "607", "608", "609", "610", "612", "614", "615",
        "616", "617", "618", "619", "620", "623", "626", "628", "629",
        "630", "631", "636", "641", "646", "650", "651", "657", "660",
        "661", "662", "667", "669", "678", "680", "681", "682", "701",
        "702", "703", "704", "706", "707", "708", "712", "713", "714",
        "715", "716", "717", "718", "719", "720", "724", "725", "727",
        "731", "732", "734", "737", "740", "743", "747", "754", "757",
        "760", "762", "763", "765", "769", "770", "772", "773", "774",
        "775", "779", "781", "785", "786", "801", "802", "803", "804",
        "805", "806", "808", "810", "812", "813", "814", "815", "816",
        "817", "818", "828", "830", "831", "832", "843", "845", "847",
        "848", "850", "856", "857", "858", "859", "860", "862", "863",
        "864", "865", "870", "878", "901", "903", "904", "906", "907",
        "908", "909", "910", "912", "913", "914", "915", "916", "917",
        "918", "919", "920", "925", "928", "929", "931", "936", "937",
        "938", "940", "941", "947", "949", "951", "952", "954", "956",
        "959", "970", "971", "972", "973", "978", "979", "980", "984",
        "985", "989"
    ]
    
    area_code = random.choice(valid_area_codes)
    # Exchange code (first digit cannot be 0 or 1)
    exchange = str(random.randint(2, 9)) + str(random.randint(0, 9)) + str(random.randint(0, 9))
    # Subscriber number
    subscriber = str(random.randint(1000, 9999))
    
    return f"{area_code}-{exchange}-{subscriber}"

def run_signin(email, password, full_name, phone_number, run_headless=True, base_url=None):
    """
    Sign in to account. Handles multiple popup scenarios:
    - Case 1: First-time login after registration (Howdy Resident + profile + bundle popup)
    - Case 2: Login with incomplete order (promotion popup + Howdy + access instructions)
    - Case 3: Login with completed orders (promotion popup + Howdy + review popup)
    
    Always keeps the browser open and returns a clean home page for further use.
    
    Args:
        email: User email
        password: User password
        full_name: Full name (for first-time login profile)
        phone_number: Phone number (for first-time login profile)
        run_headless: Whether to run browser in headless mode
        base_url: Base URL for the target website (required)
    
    Returns:
        (playwright, browser, context, page) tuple with a clean home page
    """
    if not base_url:
        raise ValueError("base_url is required")
    
    p = sync_playwright().start()
    
    # Launch browser and configure mobile environment
    browser = p.chromium.launch(headless=run_headless)
    context = browser.new_context(
        permissions=['geolocation'],
        geolocation={'latitude': 29.450411, 'longitude': -98.644806},
        # viewport={'width': 390, 'height': 844},
        # is_mobile=True,
        # user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
    )
    page = context.new_page()

    # Navigate to signin page
    print(f"Opening website: {base_url}...")
    page.goto(f"{base_url}/Welcome")

    # Click Sign in button
    print("Clicking Sign in button...")
    page.get_by_text("Sign in").click()
    
    # Enter credentials
    print(f"Entering credentials for {email}...")
    page.locator('input[type="email"]').fill(email)
    page.locator('input[type="password"]').fill(password)

    # Click Sign in button
    print("Submitting login...")
    page.get_by_text("Sign in").click()

    # Wait for page to load after login
    time.sleep(1)
    
    # ===== HANDLE ALL POPUP SCENARIOS =====
    # The key insight is that popups can appear in any combination.
    # We'll check and dismiss each type in order of likely appearance.
    
    # ------ STEP 1: Handle Promotion Popup (anticon close button) ------
    # This appears in Case 2 and Case 3
    _dismiss_promotion_popup(page)
    
    # ------ STEP 2: Handle First-Time Profile Setup ------
    # This appears in Case 1 (first login after registration)
    _handle_first_time_profile(page, full_name, phone_number)
    
    # ------ STEP 3: Handle "Howdy Resident!" Popup with Ok button ------
    # This appears in multiple cases
    _dismiss_howdy_popup(page)
    
    # ------ STEP 4: Handle Access Instructions Input ------
    # This appears in Case 2 (incomplete orders)
    _handle_access_instructions(page)
    
    # ------ STEP 5: Handle Review Popup ------
    # This appears in Case 3 (completed orders)
    _dismiss_review_popup(page)
    
    # ------ STEP 6: Handle Bundle Purchase Popup ------
    # This appears in Case 1 after profile setup
    _dismiss_bundle_popup(page)
    
    # ------ STEP 7: Final cleanup - dismiss any remaining popups ------
    _final_cleanup(page)
    
    # Return the session for reuse
    print("Sign in complete. Returning clean home page session.")
    return p, browser, context, page


def _dismiss_promotion_popup(page):
    """
    Dismiss the promotion/bundle popup (has an anticon close button).
    This popup often appears for returning users or immediately after login.
    Targeting the parent div of the anticon icon for clicking.
    """
    print("Checking for promotion/bundle popup...")
    time.sleep(2)
    
    try:
        # The user reported the close button has an anticon icon inside a tabindex="0" div.
        # We target the parent container that is clickable.
        # Selector: div[tabindex="0"] > div[style*="font-family: anticon"]
        # We click the parent.
        
        # Find all anticon icons
        anticon_icons = page.locator('div[style*="font-family: anticon"]')
        count = anticon_icons.count()
        
        if count > 0:
            print(f"Found {count} potential close buttons (anticon).")
            # Try to close the visible ones, starting from the last one (usually top of z-index)
            # The user noted "the second one is layed on the button layer of the first one", 
            # so we might need to be persistent.
            
            for i in range(count - 1, -1, -1):
                icon = anticon_icons.nth(i)
                if icon.is_visible():
                    # Try to click the parent if it exists and looks like a button
                    parent = icon.locator('..')
                    print(f"Attempting to click close button #{i}...")
                    try:
                        # Try clicking parent with forcing
                        parent.click(force=True, timeout=2000)
                        print("Clicked close button parent.")
                        time.sleep(1.5)
                        
                        # Check if popup is gone?
                        if anticon_icons.count() < count:
                             print("Popup seems to have closed.")
                             return
                    except:
                        # Fallback to clicking the icon itself
                        print("Parent click failed, clicking icon directly...")
                        icon.click(force=True, timeout=2000)
                        time.sleep(1.5)
        else:
            print("No anticon close buttons found.")

    except Exception as e:
        print(f"Error handling promotion popup: {e}")


def _handle_first_time_profile(page, full_name, phone_number):
    """
    Handle first-time login profile setup.
    CRITICAL: Validates it's actually the profile setup by looking for "Please complete your personal info".
    "Howdy Resident!" alone is NOT enough as it appears for returning users too.
    """
    print("Checking for first-time login profile setup...")
    time.sleep(2)
    
    try:
        # Strict check for the profile setup header
        # <div dir="auto" ...>Please complete your personal info</div>
        profile_header = page.locator('div[dir="auto"]', has_text="Please complete your personal info")
        
        # Also check for "Howdy Resident!" as it's part of the flow, but secondary confirmation
        greeting_text = page.locator('div[dir="auto"]', has_text="Howdy Resident!")
        
        if profile_header.is_visible(timeout=3000):
            print("First-time login profile setup DETECTED ('Please complete your personal info').")
            
            # Handle "Howdy Resident!" if present
            if greeting_text.is_visible():
                 print("Dismissing 'Howdy Resident!' greeting first...")
                 try:
                     ok_button = page.get_by_role("button", name="Ok")
                     ok_button.click(timeout=1000)
                    #  time.sleep(2)
                 except:
                     print("Could not click Ok on greeting, proceeding...")

            print("Filling in profile information...")
            
            # Fill in full name and phone number
            name_inputs = page.locator('input[data-testid="text-input-flat"]').all()
            if len(name_inputs) >= 2:
                # First input is typically the name field
                name_inputs[0].fill(full_name)
                print(f"Filled name: {full_name}")
                time.sleep(1)
                
                # Second input is typically the phone field
                name_inputs[1].fill(phone_number)
                print(f"Filled phone: {phone_number}")
                time.sleep(1)
                
                # Click Done and handle phone validation error with retry loop
                max_retries = 5
                current_phone = phone_number
                
                for attempt in range(max_retries):
                    # Click Done button
                    time.sleep(1)
                    try:
                        done_button = page.get_by_text("Done", exact=True)
                        done_button.click()
                        print(f"Clicked Done button (attempt {attempt + 1})")
                        time.sleep(2)
                    except Exception as e:
                        print(f"Could not click Done button: {e}")
                        break
                    
                    # Check if phone validation error appears
                    try:
                        phone_error = page.locator('div[dir="auto"]', has_text="This value should be a valid phone number")
                        if phone_error.is_visible(timeout=2000):
                            print(f"Warning: Phone number '{current_phone}' is not valid. Generating new number...")
                            
                            # Generate a new random valid phone number
                            current_phone = _generate_valid_phone_number()
                            print(f"Trying new phone number: {current_phone}")
                            
                            # Fill the new phone number
                            name_inputs[1].fill(current_phone)
                            time.sleep(1)
                            
                            # Continue to next attempt
                            continue
                        else:
                            # No error, popup should have closed successfully
                            print("Phone number accepted, profile setup complete.")
                            break
                    except Exception as validation_check_error:
                        # If we can't find the error, assume success and exit loop
                        print(f"Phone validation check passed or popup closed: {validation_check_error}")
                        break
                else:
                    print(f"Warning: Max retries ({max_retries}) reached for phone validation.")
                
        else:
            print("First-time profile setup NOT detected (normal for returning users).")
            # If "Howdy Resident" is present but NO "Please complete...", it will be handled by _dismiss_howdy_popup later
            
    except Exception as e:
        print(f"Error in first-time profile checks: {e}")


def _dismiss_howdy_popup(page):
    """
    Dismiss the "Howdy Resident!" popup with Ok button.
    This appears in multiple scenarios for returning users.
    """
    print("Checking for 'Howdy Resident!' popup...")
    time.sleep(2)
    
    try:
        # Look for the popup text
        if page.locator('div[dir="auto"]', has_text="Howdy Resident!").is_visible(timeout=2000):
            print("Howdy Resident popup is visible.")
            # Look for Ok button with specific testid or role
            # User provided HTML: <div ... data-testid="button-text">Ok</div>
            # Parent button often handles the click
            
            try:
                # Try button with name "Ok"
                ok_btn = page.get_by_role("button", name="Ok").last
                ok_btn.click(timeout=2000)
                print("Clicked 'Ok' on Howdy popup.")
            except:
                # Fallback to text locator
                page.locator('div[dir="auto"]', has_text="Ok").last.click(timeout=2000)
                print("Clicked 'Ok' text.")
            
            time.sleep(2)
    except Exception as e:
        print(f"No Howdy popup found/dismissed: {e}")


def _handle_access_instructions(page):
    """
    Handle the "please provide access instructions" input.
    This appears for accounts with incomplete orders (Case 2).
    Fill with "email" and click Done.
    """
    print("Checking for access instructions prompt...")
    time.sleep(2)
    
    try:
        # Look for text containing "access instructions" or similar
        access_prompt = page.locator('div[dir="auto"]', has_text="access instructions")
        if access_prompt.is_visible(timeout=1000):
            print("Access instructions prompt found. Filling in...")
            
            # Find the input field and fill with "email"
            input_field = page.locator('input[data-testid="text-input-flat"]').last
            input_field.fill("email")
            print("Filled access instructions with 'email'")
            time.sleep(1)
            
            # Click Done button
            done_button = page.get_by_text("Done", exact=True)
            done_button.click()
            print("Clicked Done on access instructions")
            # time.sleep(2)
    except Exception as e:
        print(f"No access instructions prompt found (this is normal): {e}")


def _dismiss_review_popup(page):
    """
    Dismiss the review popup that appears for accounts with completed orders (Case 3).
    Look for the close icon (anticon font).
    Reuse _dismiss_promotion_popup logic implicitly if possible or explicit here.
    """
    print("Checking for review popup...")
    # This often uses the same anticon close button as the promotion popup.
    # We can try calling _dismiss_promotion_popup or specialized logic.
    _dismiss_promotion_popup(page)


def _dismiss_bundle_popup(page):
    """
    Dismiss the "Buy Resident Bundle" popup.
    """
    print("Checking for bundle purchase popup...")
    time.sleep(2)
    
    try:
        # Look for the bundle text
        bundle_text = page.locator('div[dir="auto"]', has_text="Bundle")
        if bundle_text.is_visible(timeout=2000):
            print("Bundle popup detected.")
            # Use the robust close logic
            _dismiss_promotion_popup(page)
    except Exception as e:
        print(f"No bundle popup found check: {e}")


def _final_cleanup(page):
    """
    Final cleanup to ensure we have a clean home page.
    Dismiss any remaining popups that might have appeared.
    """
    print("Performing final cleanup...")
    time.sleep(2)
    
    # Try generic close one more time
    _dismiss_promotion_popup(page)
    
    # Try to click any "Ok" buttons that might be visible
    try:
        ok_buttons = page.get_by_text("Ok", exact=True)
        if ok_buttons.count() > 0 and ok_buttons.first.is_visible():
            ok_buttons.first.click(timeout=1000)
            print("Clicked remaining 'Ok' button.")
            time.sleep(1)
    except:
        pass
    
    # Verify we're on the home page
    try:
        home_indicator = page.locator('div[dir="auto"]', has_text="ACommerce")
        if home_indicator.is_visible(timeout=1000):
            print("Verified: On clean home page.")
        else:
            print("Warning: ACommerce marker not found. Popup might still be blocking.")
    except:
        print("Warning: Could not verify home page state.")
    
    print("Final cleanup complete.")
