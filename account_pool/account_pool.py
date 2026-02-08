import pandas as pd
import random
import os
import csv

def generate_accounts(emails, filename="account_pool.csv", locations_file="locations.csv"):
    """
    Generate account pool entries for the given list of emails.
    Each email gets assigned a random location, unit number, and phone number.
    
    Args:
        emails: List of email addresses to add to the pool
        filename: Path to the account pool CSV file
        locations_file: Path to the locations CSV file
    
    Returns:
        int: Number of accounts successfully added
    """
    # Load existing data or create empty DataFrame
    if os.path.exists(filename):
        df = pd.read_csv(filename)
    else:
        df = pd.DataFrame(columns=['email', 'geolocation', 'full_address', 'unit_number', 'phone_number', 'used'])

    # Load locations from CSV
    geo_address_pairs = load_locations(locations_file)
    
    if not geo_address_pairs:
        raise ValueError(f"No locations found in {locations_file}. Please add at least one location.")

    new_records = []
    
    # Track existing unique values to prevent duplicates
    existing_emails = set(df['email'].tolist()) if 'email' in df.columns else set()
    existing_phones = set(df['phone_number'].tolist()) if 'phone_number' in df.columns else set()
    
    added_count = 0
    
    for email in emails:
        # Skip if email already exists in pool
        if email in existing_emails:
            print(f"Skipping duplicate email: {email}")
            continue
        
        existing_emails.add(email)
        
        # Random Geo/Address Selection
        geo, address = random.choice(geo_address_pairs)
        
        # Unique Unit Number (unique per address)
        existing_units = set(df[df['full_address'] == address]['unit_number'].tolist()) if 'full_address' in df.columns else set()
        current_run_units = {r['unit_number'] for r in new_records if r['full_address'] == address}
        all_taken_units = existing_units.union(current_run_units)

        while True:
            new_unit = random.randint(100, 999)
            if new_unit not in all_taken_units:
                break
        
        # Unique Phone Number (NANP Format: NXX-NXX-XXXX)
        while True:
            area_code = random.randint(200, 999)
            exchange_code = random.randint(200, 999)
            line_number = random.randint(0, 9999)
            
            new_phone = f"{area_code}-{exchange_code}-{line_number:04d}"
            
            if new_phone not in existing_phones:
                existing_phones.add(new_phone)
                break
        
        # Create record
        new_records.append({
            'email': email,
            'geolocation': geo,
            'full_address': address,
            'unit_number': new_unit,
            'phone_number': new_phone,
            'used': False
        })
        added_count += 1

    # Append and save
    if new_records:
        new_df = pd.DataFrame(new_records)
        df = pd.concat([df, new_df], ignore_index=True)
        df.to_csv(filename, index=False)
        print(f"Successfully added {added_count} records to {filename}.")
    else:
        print("No new records to add (all emails were duplicates).")
    
    return added_count


def load_locations(locations_file="locations.csv"):
    """
    Load geo/address pairs from locations.csv.
    
    Args:
        locations_file: Path to the locations CSV file
        
    Returns:
        List of tuples: [(geolocation, full_address), ...]
    """
    if not os.path.exists(locations_file):
        return []
    
    pairs = []
    with open(locations_file, mode='r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            geo = row.get('geolocation', '').strip()
            addr = row.get('full_address', '').strip()
            if geo and addr:
                pairs.append((geo, addr))
    
    return pairs


def check_email_exists(email, filename="account_pool.csv"):
    """
    Check if an email already exists in the account pool.
    
    Args:
        email: Email address to check
        filename: Path to the account pool CSV file
        
    Returns:
        bool: True if email exists, False otherwise
    """
    if not os.path.exists(filename):
        return False
    
    df = pd.read_csv(filename)
    if 'email' not in df.columns:
        return False
    
    return email in df['email'].values


def calculate_max_dot_emails(gmail):
    """
    Calculate the maximum number of unique emails that can be generated
    using the Gmail dot trick.
    
    For a username with n characters, we can insert a dot between any two
    adjacent characters. Each position can either have a dot or not, giving
    us 2^(n-1) combinations. We subtract 1 for the original (no dots).
    
    Constraint: No consecutive dots allowed.
    
    Args:
        gmail: Gmail address (e.g., "johnsmith@gmail.com")
        
    Returns:
        int: Maximum number of unique emails (including original)
    """
    if '@' not in gmail:
        return 0
    
    username = gmail.split('@')[0].replace('.', '')  # Remove existing dots
    n = len(username)
    
    if n <= 1:
        return 1  # Just the original
    
    # With n characters, we have n-1 positions for dots
    # Each position can have a dot or not: 2^(n-1) combinations
    # This includes the original (no dots)
    max_emails = 2 ** (n - 1)
    
    return max_emails


def generate_dot_variations(gmail, count):
    """
    Generate unique email variations using the Gmail dot trick.
    Uses randomized dot placement (not sequential).
    
    Args:
        gmail: Base Gmail address (e.g., "johnsmith@gmail.com")
        count: Number of variations to generate
        
    Returns:
        List of unique email addresses (dotted variations, excluding original)
    """
    if '@' not in gmail:
        return [gmail]
    
    username = gmail.split('@')[0].replace('.', '')  # Remove existing dots
    domain = gmail.split('@')[1]
    n = len(username)
    
    if n <= 1:
        return [gmail]
    
    positions = n - 1  # Number of positions where dots can go
    
    # Generate all possible indices (skip 0 which is the original email)
    all_indices = list(range(1, 2 ** positions))
    random.shuffle(all_indices)
    
    # Take only as many as needed
    selected_indices = all_indices[:min(count, len(all_indices))]
    
    emails = []
    for i in selected_indices:
        # Build email with dots based on binary representation
        email_chars = []
        for j, char in enumerate(username):
            email_chars.append(char)
            # Check if we should add a dot after this character
            if j < positions and (i >> j) & 1:
                email_chars.append('.')
        
        new_email = ''.join(email_chars) + '@' + domain
        emails.append(new_email)
    
    return emails
