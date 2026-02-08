from flask import Flask, render_template, request, jsonify
from data_manager import DataManager
from register import run_registration, parse_geolocation
from signin import run_signin
from make_purchase import run_purchase
from update_credits import run_update_credits
import threading
import random
import re
import sys
import os
import time

# Add account_pool to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'account_pool'))
from account_pool import generate_accounts

app = Flask(__name__)

# Global state to track browser sessions
browser_sessions = {}
operation_status = {"status": "idle", "message": ""}

# Global state for generation status
generation_status = {
    "status": "idle",
    "message": "",
    "messages": [],
    "completed": 0,
    "total": 0
}

# Global state for payment feature
payment_status = {
    "status": "idle",
    "current_email": None,
    "browser_session": None,
    "message": ""
}

# Global state for credits update
credits_status = {
    "status": "idle",
    "message": "",
    "messages": [],
    "completed": 0,
    "total": 0,
    "successful": 0,
    "failed": 0,
    "current_email": None,
    "stop_requested": False
}

# Global app configuration (base URL)
app_config = {
    "base_url": None
}

dm = DataManager()

# ==========================================
# CONFIG API ENDPOINTS
# ==========================================

@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current app configuration"""
    return jsonify(app_config)

@app.route('/api/config', methods=['POST'])
def set_config():
    """Set app configuration"""
    global app_config
    data = request.json
    
    if 'base_url' in data:
        base_url = data['base_url'].rstrip('/')  # Remove trailing slash
        app_config['base_url'] = base_url
        print(f"Base URL configured: {base_url}")
        
    return jsonify({"status": "success", "config": app_config})

# ==========================================
# VALIDATION HELPERS
# ==========================================

def validate_gmail(email):
    """Validate Gmail address - must be @gmail.com, username no +, ., -"""
    errors = []
    
    if not email.lower().endswith('@gmail.com'):
        errors.append('Must be a Gmail address (@gmail.com)')
        return errors
    
    username = email.split('@')[0]
    
    if '+' in username:
        errors.append('Gmail username cannot contain "+"')
    if '.' in username:
        errors.append('Gmail username cannot contain "."')
    if '-' in username:
        errors.append('Gmail username cannot contain "-"')
    if len(username) == 0:
        errors.append('Gmail username cannot be empty')
    
    return errors

def validate_password(password):
    """Validate password - 8+ chars, lowercase, uppercase, number"""
    errors = []
    
    if len(password) < 8:
        errors.append('Password must be at least 8 characters')
    if not re.search(r'[a-z]', password):
        errors.append('Password must contain at least 1 lowercase letter')
    if not re.search(r'[A-Z]', password):
        errors.append('Password must contain at least 1 uppercase letter')
    if not re.search(r'[0-9]', password):
        errors.append('Password must contain at least 1 number')
    
    return errors

def validate_geolocation(geo):
    """Validate geolocation format - must be 'lat, long'"""
    if not geo or geo.strip() == '':
        return []
    
    errors = []
    pattern = r'^-?\d+\.?\d*,\s*-?\d+\.?\d*$'
    
    if not re.match(pattern, geo.strip()):
        errors.append('Geolocation must be in format: "29.452137, -98.642559"')
    
    return errors

# ==========================================
# ROUTES
# ==========================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generator')
def generator():
    """Serve the account generator GUI"""
    return render_template('generator.html')

@app.route('/api/data')
def get_data():
    """Returns all CSV data as JSON"""
    dm.load_data()  # Refresh from file
    return jsonify(dm.data_cache)



@app.route('/api/purchase', methods=['POST'])
def make_purchases():
    """Make purchase - either from open page or for N accounts"""
    data = request.json
    mode = data.get('mode')  # 'open_page' or 'n_accounts'
    count = int(data.get('count', 1))
    amazon_url = data.get('amazon_url', 'https://a.co/d/8uuZwOk')
    
    def run_purchases():
        global operation_status
        
        if mode == 'open_page':
            # Use the most recent browser session
            if not browser_sessions:
                operation_status = {"status": "error", "message": "No open browser session available"}
                return
            
            # Get the last added session
            uid = list(browser_sessions.keys())[-1]
            page = browser_sessions[uid]
            
            operation_status = {"status": "running", "message": "Making purchase from open page..."}
            
            try:
                run_purchase(amazon_url=amazon_url, page=page)
                operation_status = {"status": "complete", "message": "Purchase completed"}
            except Exception as e:
                operation_status = {"status": "error", "message": str(e)}
        
        elif mode == 'n_accounts':
            operation_status = {"status": "running", "message": f"Making purchases for {count} account(s)..."}
            
            # Get accounts with a card assigned
            dm.load_data()
            eligible_accounts = [row for row in dm.data_cache if row.get('card') and row.get('card').strip() != '']
            
            if not eligible_accounts:
                operation_status = {"status": "error", "message": "No accounts with card"}
                return
            
            # Limit to requested count
            accounts_to_process = eligible_accounts[:count]
            
            for i, account in enumerate(accounts_to_process):
                try:
                    print(f"[{i+1}/{len(accounts_to_process)}] Processing {account['full_name']}...")
                    
                    # Sign in and make purchase
                    p, browser, context, page = run_signin(
                        email=account['email'],
                        password=account['password'],
                        full_name=account.get('full_name', 'User'),
                        phone_number=account.get('phone_number', ''),
                        base_url=app_config['base_url']
                    )
                    
                    run_purchase(amazon_url=amazon_url, page=page)
                    
                    # Clean up
                    context.close()
                    browser.close()
                    p.stop()
                    
                except Exception as e:
                    print(f"Error processing {account['full_name']}: {e}")
            
            operation_status = {"status": "complete", "message": f"Processed {len(accounts_to_process)} account(s)"}
    
    thread = threading.Thread(target=run_purchases)
    thread.start()
    
    return jsonify({"status": "started"})

@app.route('/api/status')
def get_status():
    """Get current operation status"""
    return jsonify(operation_status)

@app.route('/api/eligible_accounts')
def get_eligible_accounts():
    """Get count of accounts eligible for purchase (has card assigned)"""
    dm.load_data()
    eligible = [row for row in dm.data_cache if row.get('card') and row.get('card').strip() != '']
    return jsonify({"count": len(eligible)})

# ==========================================
# GENERATOR HELPER API
# ==========================================

@app.route('/api/locations')
def get_locations():
    """Get all locations from locations.csv"""
    locations = dm.get_locations()
    return jsonify({
        "locations": [{"geolocation": geo, "address": addr} for geo, addr in locations],
        "count": len(locations),
        "has_locations": len(locations) > 0
    })

@app.route('/api/generator/calculate-max', methods=['POST'])
def calculate_max_accounts():
    """
    Calculate maximum number of accounts that can be generated for a Gmail address
    using the dot trick. Also filters out existing emails.
    """
    data = request.json
    email = data.get('email', '').strip()
    
    if not email or '@' not in email:
        return jsonify({"max": 0, "error": "Invalid email"})
    
    # Reload data cache to get latest
    dm.load_data()
    
    # Check if it's Gmail
    is_gmail = email.lower().endswith('@gmail.com')
    
    if not is_gmail:
        # Non-Gmail: only 1 account
        exists = dm.email_exists_in_data(email)
        return jsonify({
            "max": 0 if exists else 1,
            "is_gmail": False,
            "duplicate": exists
        })
    
    # For Gmail, calculate max based on dot trick
    # Import the function from account_pool
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'account_pool'))
    from account_pool import calculate_max_dot_emails, generate_dot_variations
    
    max_possible = calculate_max_dot_emails(email)
    
    # Generate all possible variations and filter out existing ones
    all_variations = generate_dot_variations(email, max_possible)
    
    # Filter out emails that already exist in account_data.csv
    available = [e for e in all_variations if not dm.email_exists_in_data(e)]
    
    return jsonify({
        "max": len(available),
        "total_possible": max_possible,
        "is_gmail": True,
        "duplicates_filtered": max_possible - len(available)
    })

# ==========================================
# ACCOUNT GENERATOR API
# ==========================================


@app.route('/api/generate', methods=['POST'])
def generate_accounts_api():
    """
    Generate and register new accounts directly.
    Creates email variations in memory and registers them to account_data.csv.
    """
    global generation_status
    
    data = request.json
    
    try:
        count = int(data.get('count', 1))
    except (ValueError, TypeError):
        count = 1
        
    email = data.get('email', '').strip()
    password = data.get('password', '')
    is_gmail = data.get('isGmail', True)
    geolocation = data.get('geolocation', '').strip()
    full_address = data.get('fullAddress', '').strip()
    
    # Validation
    all_errors = []
    
    if not email or '@' not in email:
        all_errors.append('Valid email address is required')
        
    all_errors.extend(validate_password(password))
    all_errors.extend(validate_geolocation(geolocation))
    
    # Check geo + address consistency
    has_geo = geolocation != ''
    has_address = full_address != ''
    if has_geo != has_address:
        all_errors.append('If adding a new location, both Geolocation AND Full Address are required')
    
    # Check if locations exist
    locations = dm.get_locations()
    if not locations and not (has_geo and has_address):
        all_errors.append('No locations available. Please add a location in locations.csv or provide one manually.')
        
    if all_errors:
        return jsonify({"status": "error", "errors": all_errors})
    
    # Reset status
    generation_status = {
        "status": "running",
        "message": "Starting generation...",
        "messages": [],
        "completed": 0,
        "total": count
    }
    
    def run_generation():
        global generation_status
        
        try:
            # Import account_pool functions for email generation
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'account_pool'))
            from account_pool import generate_dot_variations
            
            # Step 1: Generate email variations in memory
            if is_gmail:
                add_message(f"Generating {count} email variations using dot trick...", "info")
                all_variations = generate_dot_variations(email, count)
                
                # Filter out duplicates (already in account_data.csv)
                dm.load_data()
                emails_to_register = [e for e in all_variations if not dm.email_exists_in_data(e)]
                
                if len(emails_to_register) < len(all_variations):
                    filtered = len(all_variations) - len(emails_to_register)
                    add_message(f"Filtered {filtered} duplicate emails", "warning")
                
                if not emails_to_register:
                    add_message("All email variations already exist!", "error")
                    generation_status["status"] = "error"
                    generation_status["message"] = "No new emails to register"
                    return
            else:
                # Non-Gmail: single email
                dm.load_data()
                if dm.email_exists_in_data(email):
                    add_message(f"Email {email} already exists!", "error")
                    generation_status["status"] = "error"
                    generation_status["message"] = "Email already exists"
                    return
                emails_to_register = [email]
            
            # Limit to requested count
            emails_to_register = emails_to_register[:count]
            
            # Step 2: Prepare account data in memory
            locations_list = dm.get_locations()
            
            # If user provided custom location, add it
            if geolocation and full_address:
                add_message(f"Using custom location: {full_address}", "info")
                locations_list.append((geolocation, full_address))
                # Also save to locations.csv for future use
                locations_file = os.path.join(os.path.dirname(__file__), 'locations.csv')
                with open(locations_file, 'a', newline='', encoding='utf-8') as f:
                    import csv
                    writer = csv.writer(f)
                    writer.writerow([geolocation, full_address])
            
            accounts_to_register = []
            for email_addr in emails_to_register:
                # Pick random location
                geo, addr = random.choice(locations_list)
                
                # Generate random details
                unit_number = str(random.randint(100, 999))
                phone_number = f"{random.randint(200,999)}-{random.randint(200,999)}-{random.randint(1000,9999)}"
                
                accounts_to_register.append({
                    'email': email_addr,
                    'geolocation': geo,
                    'full_address': addr,
                    'unit_number': unit_number,
                    'phone_number': phone_number
                })
            
            add_message(f"Prepared {len(accounts_to_register)} accounts for registration", "info")
            
            # Step 3: Register each account
            generation_status["total"] = len(accounts_to_register)
            successful = 0
            
            for i, account_data in enumerate(accounts_to_register):
                generation_status["completed"] = i
                
                pool_email = account_data['email']
                raw_geo = account_data['geolocation']
                full_addr = account_data['full_address']
                unit_number = account_data['unit_number']
                phone_number = account_data['phone_number']
                
                add_message(f"[{i+1}/{len(accounts_to_register)}] Registering {pool_email}...", "info")
                
                # Generate UID
                uid = dm.generate_uid()
                
                # Parse geolocation
                geo_dict = parse_geolocation(raw_geo)
                
                # Get register page (with referral if available)
                register_page, referrer_uid = dm.get_register_page(use_refer=True, base_url=app_config['base_url'])
                
                # Run registration
                success = run_registration(
                    register_page=register_page,
                    email=pool_email,
                    password=password,
                    geolocation=geo_dict,
                    full_address=full_addr,
                    unit_number=unit_number
                )
                
                if success:
                    # Generate a display name from email
                    display_name = pool_email.split('@')[0].replace('.', ' ').replace('_', ' ').title()
                    
                    # Save to database
                    row_data = {
                        "UID": uid,
                        "register_page": register_page,
                        "email": pool_email,
                        "password": password,
                        "geolocation": str(geo_dict),
                        "full_address": full_addr,
                        "unit_number": unit_number,
                        "full_name": display_name,
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
                    
                    # Increment referrer's count
                    if referrer_uid:
                        dm.increment_referral_amount(referrer_uid)
                    
                    successful += 1
                    add_message(f"✓ {pool_email} registered successfully", "success")
                else:
                    add_message(f"✗ Registration failed for {pool_email}", "error")
            
            generation_status["completed"] = len(accounts_to_register)
            generation_status["status"] = "complete"
            generation_status["message"] = f"Completed {successful}/{len(accounts_to_register)} account(s)"
            add_message(f"🎉 Process complete! {successful}/{len(accounts_to_register)} account(s) registered.", "success")
            
        except Exception as e:
            generation_status["status"] = "error"
            generation_status["message"] = str(e)
            add_message(f"Error: {str(e)}", "error")
    
    # Start in background thread
    thread = threading.Thread(target=run_generation)
    thread.start()
    
    return jsonify({"status": "started"})

def add_message(text, msg_type="info"):
    """Add a message to the generation status for frontend display"""
    global generation_status
    generation_status["messages"].append({
        "text": text,
        "type": msg_type
    })
    print(f"[{msg_type.upper()}] {text}")

@app.route('/api/generate/status')
def get_generation_status():
    """Get current generation status and messages"""
    global generation_status
    
    # Return and clear messages to avoid duplicates
    response = {
        "status": generation_status["status"],
        "message": generation_status["message"],
        "messages": generation_status["messages"],
        "completed": generation_status["completed"],
        "total": generation_status["total"]
    }
    
    # Clear consumed messages
    generation_status["messages"] = []
    
    return jsonify(response)

# ==========================================
# PAGE ROUTES
# ==========================================

@app.route('/payment')
def payment_page():
    """Serve the update payment GUI"""
    return render_template('payment.html')

@app.route('/credits')
def credits_page():
    """Serve the update credit GUI"""
    return render_template('credits.html')

@app.route('/purchase')
def purchase_page():
    """Serve the make purchase GUI (placeholder)"""
    return render_template('purchase.html')

# ==========================================
# PAYMENT API ENDPOINTS
# ==========================================

# Track skipped emails for this session
skipped_emails = set()

@app.route('/api/payment/stats')
def get_payment_stats():
    """Get payment statistics - total accounts and accounts without payment"""
    dm.load_data()
    
    total = len(dm.data_cache)
    # Find accounts without payment
    no_payment = [row for row in dm.data_cache if not row.get('card') or row.get('card').strip() == '']
    
    # Filter out skipped emails for the "next account" suggestion
    available_accounts = [row for row in no_payment if row.get('email') not in skipped_emails]
    
    # Get the first available account without payment
    next_account = None
    if available_accounts:
        next_account = {
            'email': available_accounts[0].get('email'),
            'full_name': available_accounts[0].get('full_name'),
            'password': available_accounts[0].get('password'),
            'phone_number': available_accounts[0].get('phone_number')
        }
    
    return jsonify({
        'total': total,
        'no_payment': len(no_payment), # Keep total count accurate
        'next_account': next_account
    })

@app.route('/api/payment/start', methods=['POST'])
def start_payment():
    """Start signin for an account and navigate to payment page (opens browser in visible mode)"""
    global payment_status
    # Clear skipped list for this specific email if they decide to process it now
    data = request.json
    email = data.get('email')
    if email and email in skipped_emails:
        skipped_emails.remove(email)
        
    if not email:
        return jsonify({'status': 'error', 'message': 'Email is required'})
    
    # Find account in data
    dm.load_data()
    account = None
    for row in dm.data_cache:
        if row.get('email') == email:
            account = row
            break
    
    if not account:
        return jsonify({'status': 'error', 'message': f'Account {email} not found'})
    
    def run_signin_and_navigate():
        global payment_status
        try:
            # Import signin and update_payment functions
            from signin import run_signin
            from update_payment import navigate_to_payment_page
            
            payment_status = {
                'status': 'logging_in',
                'current_email': email,
                'browser_session': None,
                'message': 'Logging in and navigating to payment page...'
            }
            
            # Use signin.py to login (run_headless=False for visible browser)
            p, browser, context, page = run_signin(
                email=account['email'],
                password=account['password'],
                full_name=account.get('full_name', 'User'),
                phone_number=account.get('phone_number', ''),
                run_headless=False,
                base_url=app_config['base_url']
            )
            
            payment_status['message'] = 'Logged in. Navigating to payment page...'
            
            # Navigate to the payment input page
            page = navigate_to_payment_page(page)
            
            # Store session info
            payment_status = {
                'status': 'browser_open',
                'current_email': email,
                'browser_session': {'p': p, 'browser': browser, 'context': context, 'page': page},
                'message': 'Ready! Please enter credit card details manually.'
            }
            
        except Exception as e:
            payment_status = {
                'status': 'error',
                'current_email': email,
                'browser_session': None,
                'message': str(e)
            }
    
    # Run in background thread
    thread = threading.Thread(target=run_signin_and_navigate)
    thread.start()
    
    # Wait a moment for thread to start
    time.sleep(1)
    
    return jsonify({'status': 'success', 'message': 'Logging in and navigating to payment page...'})


@app.route('/api/payment/set-alias', methods=['POST'])
def set_payment_alias():
    """Set the card alias for an account"""
    global payment_status
    
    data = request.json
    email = data.get('email')
    card_alias = data.get('card_alias')
    
    if not email or not card_alias:
        return jsonify({'status': 'error', 'message': 'Email and card_alias are required'})
    
    # Update the CSV
    dm.load_data()
    updated = False
    
    for row in dm.data_cache:
        if row.get('email') == email:
            row['card'] = card_alias
            updated = True
            break
    
    if not updated:
        return jsonify({'status': 'error', 'message': f'Account {email} not found'})
    
    # Write back to file
    import csv
    with open(dm.OUTPUT_FILE, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=dm.OUTPUT_COLUMNS)
        writer.writeheader()
        for row in dm.data_cache:
            cleaned_row = {col: row.get(col, '') for col in dm.OUTPUT_COLUMNS}
            writer.writerow(cleaned_row)
    
    # Close browser if it's open
    if payment_status.get('browser_session'):
        try:
            session = payment_status['browser_session']
            session['browser'].close()
            session['p'].stop()
        except:
            pass
    
    # Reset payment status
    payment_status = {
        'status': 'idle',
        'current_email': None,
        'browser_session': None,
        'message': ''
    }
    
    return jsonify({'status': 'success', 'message': f'Card alias set for {email}'})

@app.route('/api/payment/skip', methods=['POST'])
def skip_payment_account():
    """Skip the current account and close browser"""
    global payment_status
    
    data = request.json
    email = data.get('email')
    
    if email:
        skipped_emails.add(email)
        print(f"Skipping account: {email}")
    
    # Close browser if open
    if payment_status.get('browser_session'):
        try:
            session = payment_status['browser_session']
            session['browser'].close()
            session['p'].stop()
        except:
            pass
    
    # Reset status
    payment_status = {
        'status': 'idle',
        'current_email': None,
        'browser_session': None,
        'message': ''
    }
    
    return jsonify({'status': 'success', 'message': 'Account skipped'})

# ==========================================
# CREDITS API ENDPOINTS
# ==========================================

def add_credits_message(text, msg_type="info"):
    """Add a message to the credits status for frontend display"""
    global credits_status
    credits_status["messages"].append({
        "text": text,
        "type": msg_type
    })
    print(f"[CREDITS-{msg_type.upper()}] {text}")

@app.route('/api/credits/update-all', methods=['POST'])
def update_all_credits():
    """Start updating credits for all accounts"""
    global credits_status
    
    # Reset status
    credits_status = {
        "status": "running",
        "message": "Starting credit update...",
        "messages": [],
        "completed": 0,
        "total": 0,
        "successful": 0,
        "failed": 0,
        "current_email": None,
        "stop_requested": False
    }
    
    def run_credits_update():
        global credits_status
        
        try:
            dm.load_data()
            accounts = [row for row in dm.data_cache if row.get('email') and row.get('password')]
            
            credits_status["total"] = len(accounts)
            add_credits_message(f"Found {len(accounts)} accounts to process", "info")
            
            for idx, account in enumerate(accounts):
                # Check if stop was requested
                if credits_status["stop_requested"]:
                    add_credits_message("Stop requested. Finishing current account...", "warning")
                    break
                
                email = account['email']
                password = account['password']
                full_name = account.get('full_name', '')
                phone_number = account.get('phone_number', '')
                
                credits_status["current_email"] = email
                credits_status["completed"] = idx
                
                add_credits_message(f"[{idx+1}/{len(accounts)}] Processing {email}...", "info")
                
                try:
                    # Sign in (headless)
                    p, browser, context, page = run_signin(email, password, full_name, phone_number, base_url=app_config['base_url'])
                    
                    # Update credits
                    credit_value = run_update_credits(email, page)
                    
                    add_credits_message(f"✓ {email}: ${credit_value}", "success")
                    credits_status["successful"] += 1
                    
                    # Close browser
                    browser.close()
                    p.stop()
                    
                    # Small delay between accounts
                    time.sleep(1)
                    
                except Exception as e:
                    add_credits_message(f"✗ {email}: {str(e)}", "error")
                    credits_status["failed"] += 1
                    
                    # Try to close browser on error
                    try:
                        browser.close()
                        p.stop()
                    except:
                        pass
            
            credits_status["completed"] = len(accounts)
            
            if credits_status["stop_requested"]:
                credits_status["status"] = "stopped"
                credits_status["message"] = "Update stopped by user"
            else:
                credits_status["status"] = "complete"
                credits_status["message"] = "Credit update complete!"
                add_credits_message(f"Complete! {credits_status['successful']} successful, {credits_status['failed']} failed.", "success")
            
        except Exception as e:
            credits_status["status"] = "error"
            credits_status["message"] = str(e)
            add_credits_message(f"Error: {str(e)}", "error")
    
    # Run in background thread
    thread = threading.Thread(target=run_credits_update)
    thread.start()
    
    return jsonify({"status": "started"})

@app.route('/api/credits/status')
def get_credits_status():
    """Get current credits update status"""
    global credits_status
    
    response = {
        "status": credits_status["status"],
        "message": credits_status["message"],
        "messages": credits_status["messages"],
        "completed": credits_status["completed"],
        "total": credits_status["total"],
        "successful": credits_status["successful"],
        "failed": credits_status["failed"],
        "current_email": credits_status["current_email"]
    }
    
    # Clear consumed messages
    credits_status["messages"] = []
    
    return jsonify(response)

@app.route('/api/credits/update-from', methods=['POST'])
def update_credits_from():
    """Start updating credits from a specific account"""
    global credits_status
    
    data = request.json
    start_email = data.get('start_email')
    
    if not start_email:
        return jsonify({"status": "error", "message": "start_email is required"})
    
    # Reset status
    credits_status = {
        "status": "running",
        "message": f"Starting from {start_email}...",
        "messages": [],
        "completed": 0,
        "total": 0,
        "successful": 0,
        "failed": 0,
        "current_email": None,
        "stop_requested": False
    }
    
    def run_credits_update_from():
        global credits_status
        
        try:
            dm.load_data()
            all_accounts = [row for row in dm.data_cache if row.get('email') and row.get('password')]
            
            # Find starting index
            start_idx = 0
            for idx, acc in enumerate(all_accounts):
                if acc.get('email') == start_email:
                    start_idx = idx
                    break
            
            # Slice accounts from starting point
            accounts = all_accounts[start_idx:]
            
            credits_status["total"] = len(accounts)
            add_credits_message(f"Starting from {start_email} ({len(accounts)} accounts remaining)", "info")
            
            for idx, account in enumerate(accounts):
                # Check if stop was requested
                if credits_status["stop_requested"]:
                    add_credits_message("Stop requested. Finishing current account...", "warning")
                    break
                
                email = account['email']
                password = account['password']
                full_name = account.get('full_name', '')
                phone_number = account.get('phone_number', '')
                
                credits_status["current_email"] = email
                credits_status["completed"] = idx
                
                add_credits_message(f"[{idx+1}/{len(accounts)}] Processing {email}...", "info")
                
                try:
                    # Sign in (headless)
                    p, browser, context, page = run_signin(email, password, full_name, phone_number, base_url=app_config['base_url'])
                    
                    # Update credits
                    credit_value = run_update_credits(email, page)
                    
                    add_credits_message(f"✓ {email}: ${credit_value}", "success")
                    credits_status["successful"] += 1
                    
                    # Close browser
                    browser.close()
                    p.stop()
                    
                    # Small delay between accounts
                    time.sleep(1)
                    
                except Exception as e:
                    add_credits_message(f"✗ {email}: {str(e)}", "error")
                    credits_status["failed"] += 1
                    
                    # Try to close browser on error
                    try:
                        browser.close()
                        p.stop()
                    except:
                        pass
            
            credits_status["completed"] = len(accounts)
            
            if credits_status["stop_requested"]:
                credits_status["status"] = "stopped"
                credits_status["message"] = "Update stopped by user"
            else:
                credits_status["status"] = "complete"
                credits_status["message"] = "Credit update complete!"
                add_credits_message(f"Complete! {credits_status['successful']} successful, {credits_status['failed']} failed.", "success")
            
        except Exception as e:
            credits_status["status"] = "error"
            credits_status["message"] = str(e)
            add_credits_message(f"Error: {str(e)}", "error")
    
    # Run in background thread
    thread = threading.Thread(target=run_credits_update_from)
    thread.start()
    
    return jsonify({"status": "started"})

@app.route('/api/credits/stop', methods=['POST'])
def stop_credits_update():
    """Request stop of credits update"""
    global credits_status
    credits_status["stop_requested"] = True
    return jsonify({"status": "stop_requested"})

# ==========================================
# PURCHASE API ENDPOINTS
# ==========================================

# Track active purchase sessions
# Format: { 'email': {'p': p, 'browser': browser, 'context': context, 'page': page, 'status': 'ready'} }
purchase_sessions = {}

@app.route('/api/purchase/accounts')
def get_purchase_accounts():
    """Get all accounts and eligible accounts (has card assigned)"""
    dm.load_data()
    
    all_accounts = dm.data_cache
    eligible = []
    
    for row in all_accounts:
        # Check card only
        has_card = row.get('card') and row.get('card').strip() != ''
        
        if has_card:
            eligible.append(row)
            
    return jsonify({
        'all_accounts': all_accounts,
        'eligible_accounts': eligible
    })

@app.route('/api/merchandise')
def get_merchandise():
    """Get all merchandise items"""
    items = dm.get_merchandise()
    return jsonify({'merchandise': items})

@app.route('/api/merchandise/add', methods=['POST'])
def add_merchandise():
    """Add new merchandise item"""
    data = request.json
    name = data.get('name')
    url = data.get('url')
    
    if not name or not url:
        return jsonify({'status': 'error', 'message': 'Name and URL required'})
        
    dm.add_merchandise(name, url)
    return jsonify({'status': 'success'})

@app.route('/api/purchase/start', methods=['POST'])
def start_purchase_session():
    """Start a visible browser session for an account to make purchases"""
    data = request.json
    email = data.get('email')
    
    if not email:
        return jsonify({'status': 'error', 'message': 'Email required'})
        
    # Check if already running
    if email in purchase_sessions:
        return jsonify({'status': 'error', 'message': 'Session already active for this email'})
        
    # Find account info
    dm.load_data()
    account = None
    for row in dm.data_cache:
        if row.get('email') == email:
            account = row
            break
            
    if not account:
        return jsonify({'status': 'error', 'message': 'Account not found'})
        
    def run_session():
        try:
            from signin import run_signin
            from make_purchase import navigate_to_purchase_page
            
            # 1. Sign in (Visible)
            p, browser, context, page = run_signin(
                email=account['email'],
                password=account['password'],
                full_name=account.get('full_name', 'User'),
                phone_number=account.get('phone_number', ''),
                run_headless=False,
                base_url=app_config['base_url']
            )
            
            # 2. Navigate to BYOP
            page = navigate_to_purchase_page(page)
            
            # 3. Store session
            purchase_sessions[email] = {
                'p': p,
                'browser': browser,
                'context': context,
                'page': page,
                'status': 'ready'
            }
            
        except Exception as e:
            print(f"Error in purchase session for {email}: {e}")
            if email in purchase_sessions:
                del purchase_sessions[email]
    
    # Run in background
    thread = threading.Thread(target=run_session)
    thread.start()
    
    # Add placeholder to map immediately so we know it's starting
    purchase_sessions[email] = {'status': 'initializing'}
    
    return jsonify({'status': 'success'})

@app.route('/api/purchase/sessions')
def get_purchase_sessions():
    """Get list of active sessions"""
    sessions_list = []
    for email, session in purchase_sessions.items():
        if isinstance(session, dict):
            sessions_list.append({
                'email': email,
                'status': session.get('status', 'unknown')
            })
            
    return jsonify({'sessions': sessions_list})

@app.route('/api/purchase/stop', methods=['POST'])
def stop_purchase_session():
    """Close a purchase session"""
    data = request.json
    email = data.get('email')
    
    if email in purchase_sessions:
        session = purchase_sessions[email]
        
        # If it's fully initialized (has browser objects)
        if session.get('browser'):
            try:
                session['browser'].close()
                session['p'].stop()
            except:
                pass
        
        del purchase_sessions[email]
        return jsonify({'status': 'success'})
        
    return jsonify({'status': 'error', 'message': 'Session not found'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5011)
