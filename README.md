# Apartment Account Automation

A web-based automation tool for managing Apartment accounts. Features include:

- **Account Generator**: Create new accounts using Gmail dot variations
- **Payment Manager**: Manage payment methods for accounts
- **Make Purchase**: Open browser sessions for making purchases
- **Credit Tracker**: Track and update account credit balances

## Prerequisites

### 1. Install Python

**macOS:**
```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python 3.11+
brew install python@3.11
```

**Windows:**
1. Download Python from [python.org](https://www.python.org/downloads/)
2. Run the installer and **check "Add Python to PATH"**
3. Click "Install Now"

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv
```

### 2. Verify Installation

```bash
python3 --version  # Should show Python 3.11+
```

## Installation

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd Apartment
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv .venv

# Activate it
# macOS/Linux:
source .venv/bin/activate

# Windows:
.venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install flask playwright pandas
```

### 4. Install Playwright Browsers

```bash
playwright install chromium
```

## Configuration Files

The project uses CSV files for data storage:

| File | Purpose |
|------|---------|
| `account_data.csv` | Registered accounts (auto-created) |
| `locations.csv` | Available apartment locations |
| `merchandise.csv` | Saved merchandise URLs |

### Setting Up Locations

Create or edit `locations.csv` with your apartment locations:

```csv
geolocation,full_address
"12,99999999, 34.8888888","123 Road, Springfiled, XY"
```

## Running the Application

### Start the Server

```bash
# Make sure virtual environment is activated
source .venv/bin/activate  # macOS/Linux
# OR
.venv\Scripts\activate      # Windows

# Run the application
python main.py
```

The server will start at:
- Local: `http://127.0.0.1:5011`
- Network: `http://<your-ip>:5011`

### Access the Dashboard

Open your browser and navigate to `http://localhost:5011`

## Features

### 🏠 Dashboard (`/`)
- Configure base URL
- View all registered accounts
- Access other features

### 📝 Account Generator (`/generator`)
- Enter Gmail address for dot variations
- Set password (8+ chars, upper, lower, number)
- Select number of accounts to create
- Optionally add new apartment locations

### 💳 Payment Manager (`/payment`)
- View accounts by card assignment
- Open browser to add payment methods
- Track payment status

### 🛒 Make Purchase (`/purchase`)
- View eligible accounts (with card assigned)
- Open marketplace browser sessions
- Manage saved merchandise URLs

### 💰 Credits (`/credits`)
- View account credit balances
- Update credits for individual accounts

## Project Structure

```
Apartment/
├── main.py              # Flask server and API routes
├── data_manager.py      # CSV data handling
├── register.py          # Account registration automation
├── signin.py            # Sign-in automation
├── make_purchase.py     # Purchase flow automation
├── update_payment.py    # Payment update automation
├── update_credits.py    # Credit balance automation
├── account_pool/        # Email variation generator
├── static/              # CSS and JavaScript files
├── templates/           # HTML templates
├── account_data.csv     # Account database
├── locations.csv        # Apartment locations
└── merchandise.csv      # Saved product URLs
```

## Troubleshooting

### "playwright install" fails
```bash
# Try with sudo on Linux/macOS
sudo playwright install chromium
```

### Browser automation issues
The automation uses Playwright with Chromium. If popups or elements aren't being detected:
1. The website UI may have changed
2. Check the terminal output for specific errors
3. Try running with `headless=False` in the code for debugging

### Port already in use
```bash
# Kill process on port 5011
lsof -ti:5011 | xargs kill -9
```

## License

This project is for personal use only.
