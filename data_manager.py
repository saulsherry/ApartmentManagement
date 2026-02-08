import csv
import os
import uuid
import random

class DataManager:
    # Output file (Registered accounts)
    OUTPUT_FILE = "account_data.csv"
    OUTPUT_COLUMNS = [
        "UID", "register_page", "email", "password", "geolocation", 
        "full_address", "unit_number", "phone_number", "full_name", 
        "card", "received_amount", "paid_amount", "refer_link", "refer_by","refer_amount",
        "unfull_filled", "remain_credit"
    ]
    
    # Locations file
    LOCATIONS_FILE = "locations.csv"
    
    # Merchandise file
    MERCHANDISE_FILE = "merchandise.csv"

    def __init__(self):
        self.data_cache = []
        self._ensure_file_exists()
        self.load_data()

    def get_merchandise(self):
        """
        Load merchandise from merchandise.csv.
        Returns list of dicts: [{'name': '...', 'url': '...'}, ...]
        """
        if not os.path.exists(self.MERCHANDISE_FILE):
            return []
            
        items = []
        with open(self.MERCHANDISE_FILE, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('name') and row.get('url'):
                    items.append({
                        'name': row['name'],
                        'url': row['url']
                    })
        return items

    def add_merchandise(self, name, url):
        """
        Add a new merchandise item to the CSV.
        """
        fieldnames = ['name', 'url']
        file_exists = os.path.exists(self.MERCHANDISE_FILE)
        
        with open(self.MERCHANDISE_FILE, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow({'name': name, 'url': url})

    def _ensure_file_exists(self):
        if not os.path.exists(self.OUTPUT_FILE):
            with open(self.OUTPUT_FILE, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.OUTPUT_COLUMNS)
                writer.writeheader()

    def load_data(self):
        """Reads the registered accounts CSV into memory."""
        self.data_cache = []
        if os.path.exists(self.OUTPUT_FILE):
            with open(self.OUTPUT_FILE, mode='r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                self.data_cache = list(reader)
        return self.data_cache

    # ==========================
    #  EMAIL DUPLICATE CHECK
    # ==========================

    def email_exists_in_data(self, email):
        """
        Check if an email already exists in account_data.csv.
        
        Args:
            email: Email address to check
            
        Returns:
            bool: True if email exists, False otherwise
        """
        for row in self.data_cache:
            if row.get('email') == email:
                return True
        return False

    # ==========================
    #  EXISTING METHODS
    # ==========================

    def save_row(self, row_data):
        """Appends a new row to the account_data.csv."""
        complete_row = {col: row_data.get(col, "") for col in self.OUTPUT_COLUMNS}
        
        # Add to cache
        self.data_cache.append(complete_row)
        
        # Rewrite entire file to ensure column consistency
        with open(self.OUTPUT_FILE, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.OUTPUT_COLUMNS)
            writer.writeheader()
            for row in self.data_cache:
                cleaned_row = {col: row.get(col, '') for col in self.OUTPUT_COLUMNS}
                writer.writerow(cleaned_row)

    def get_register_page(self, use_refer=True, base_url=None):
        """Get registration page URL, optionally using referral links."""
        default_page = base_url if base_url else ""
        if not base_url:
            raise ValueError("base_url is required")
        if not use_refer:
            return default_page, None
        
        referral_map = {}
        for row in self.data_cache:
            if row.get('refer_link'):
                uid = row.get('UID', '')
                refer_link = row['refer_link']
                refer_amount_str = row.get('refer_amount', '0')
                try:
                    refer_amount = int(refer_amount_str) if refer_amount_str else 0
                except ValueError:
                    refer_amount = 0
                
                referral_map[uid] = {'refer_link': refer_link, 'refer_amount': refer_amount}
        
        if not referral_map:
            return default_page, None
        
        odd_accounts = []
        zero_refer_accounts = []
        even_positive_accounts = []
        
        for uid, data in referral_map.items():
            amount = data['refer_amount']
            if amount % 2 == 1:
                odd_accounts.append((uid, data))
            elif amount == 0:
                zero_refer_accounts.append((uid, data))
            else:
                even_positive_accounts.append((uid, data))
        
        # Priority 1: Odd referral accounts (to make them even)
        if odd_accounts:
            odd_accounts.sort(key=lambda x: x[1]['refer_amount'])
            return odd_accounts[0][1]['refer_link'], odd_accounts[0][0]
        
        # Priority 2: Zero referral accounts
        if zero_refer_accounts:
            return zero_refer_accounts[0][1]['refer_link'], zero_refer_accounts[0][0]

        # Priority 3: Smallest even referral account
        if even_positive_accounts:
            even_positive_accounts.sort(key=lambda x: x[1]['refer_amount'])
            return even_positive_accounts[0][1]['refer_link'], even_positive_accounts[0][0]
        
        return default_page, None

    def generate_email(self, name, gmail=None):
        """
        Generates email using Gmail alias feature.
        Format: {gmail_username}+{sanitized_name}@gmail.com
        Example: john@gmail.com -> john+UserABC123@gmail.com
        
        Args:
            name: User name to create alias from
            gmail: Gmail address (required from GUI)
        
        Returns:
            Generated email address or raises error if gmail not provided
        """
        if gmail is None:
            raise ValueError("Gmail address is required. Please provide via GUI.")
        
        if '@' not in gmail:
            raise ValueError("Invalid Gmail format. Must be a valid email address.")
        
        username = gmail.split('@')[0]
        # Sanitize name: remove underscores and spaces
        sanitized_name = name.replace("_", "").replace(" ", "")
        # Generate Gmail alias
        email = f"{username}+{sanitized_name}@gmail.com"
        return email

    def get_password(self, password=None):
        """
        Returns the user-provided password.
        
        Password requirements:
        - At least 8 characters long
        - At least 1 lowercase letter
        - At least 1 uppercase letter
        - At least 1 number
        
        Args:
            password: Password string (required from GUI)
        
        Returns:
            Password string or raises error if not provided
        """
        if password is None:
            raise ValueError("Password is required. Please provide via GUI.")
        return password

    def generate_uid(self):
        return str(uuid.uuid4())

    def check_name_unique(self, name):
        existing_names = {row['full_name'] for row in self.data_cache}
        return name not in existing_names

    def increment_referral_amount(self, referrer_uid):
        """Increments the refer_amount for the given UID."""
        if not referrer_uid:
            return

        updated = False
        
        # Work with the in-memory cache to avoid race conditions
        for row in self.data_cache:
            if row.get('UID') == referrer_uid:
                current_amount = int(row.get('refer_amount', 0) or 0)
                row['refer_amount'] = str(current_amount + 1)
                updated = True
                break
        
        if updated:
            # Rewrite the entire file with updated data from cache
            with open(self.OUTPUT_FILE, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.OUTPUT_COLUMNS)
                writer.writeheader()
                # Ensure we only write valid columns
                for row in self.data_cache:
                    cleaned_row = {col: row.get(col, '') for col in self.OUTPUT_COLUMNS}
                    writer.writerow(cleaned_row)
            print(f"Incremented referral amount for UID {referrer_uid}")

    def update_remain_credit(self, email, credit_value):
        """Updates the remain_credit for the account with the given email."""
        if not email:
            return
        
        updated = False
        
        # Work with the in-memory cache
        for row in self.data_cache:
            if row.get('email') == email:
                row['remain_credit'] = str(credit_value)
                updated = True
                break
        
        if updated:
            # Rewrite the entire file with updated data from cache
            with open(self.OUTPUT_FILE, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.OUTPUT_COLUMNS)
                writer.writeheader()
                for row in self.data_cache:
                    cleaned_row = {col: row.get(col, '') for col in self.OUTPUT_COLUMNS}
                    writer.writerow(cleaned_row)
            print(f"Updated remain_credit for {email}: ${credit_value}")
        else:
            print(f"Warning: Email {email} not found in database")

    def get_locations(self):
        """
        Load locations from locations.csv file.
        
        Returns:
            List of tuples: [(geolocation, full_address), ...] or empty list if file doesn't exist
        """
        if not os.path.exists(self.LOCATIONS_FILE):
            return []
        
        locations = []
        with open(self.LOCATIONS_FILE, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                geo = row.get('geolocation', '').strip()
                addr = row.get('full_address', '').strip()
                if geo and addr:
                    locations.append((geo, addr))
        
        return locations