import sqlite3
import bcrypt
import random
from datetime import datetime, timedelta

DB_PATH = "bank.db"

FAQS = [
    ("How do I reset my password?", "To reset your password, click 'Forgot Password' on the login page, enter your registered email address, and follow the link sent to your email. If you need further assistance, call our support line at 1-800-555-0100."),
    ("How do I dispute a charge?", "To dispute a charge, log in to your account, navigate to the transaction in question, and click 'Dispute Transaction'. Fill out the dispute form with details about the issue. Our team will review within 5–7 business days."),
    ("What are the branch hours?", "Most PalBank branches are open Monday–Friday 9:00 AM to 5:00 PM, and Saturday 9:00 AM to 1:00 PM. Branches are closed on Sundays and federal holidays. Use our branch locator for specific location hours."),
    ("How do I set up direct deposit?", "To set up direct deposit, provide your employer with PalBank's routing number (021000021) and your account number. You can find these on the bottom of your checks or in the 'Account Details' section of online banking."),
    ("How do I order a new debit card?", "You can order a new debit card by logging into online banking, going to 'Card Services', and selecting 'Order Replacement Card'. Cards typically arrive within 5–7 business days. You can also visit any branch or call 1-800-555-0100."),
    ("What is the routing number?", "PalBank's routing number is 021000021. This 9-digit number is used for ACH transfers, direct deposits, and wire transfers. You can also find it on the bottom left of your personal checks."),
    ("How do I transfer money between accounts?", "Log in to online banking, select 'Transfers' from the main menu, choose the source and destination accounts, enter the amount, and confirm the transfer. Transfers between PalBank accounts are immediate and free."),
    ("What are the overdraft fees?", "PalBank charges a $35 overdraft fee per transaction if your account balance goes negative. We offer Overdraft Protection — link a savings account or credit card to automatically cover shortfalls. You can opt in through online banking or at a branch."),
    ("How do I open a new account?", "You can open a new checking or savings account online at our website, via our mobile app, or by visiting any branch. You'll need a government-issued ID, Social Security Number, and an initial deposit (minimum $25 for checking, $50 for savings)."),
    ("What is the minimum balance to avoid fees?", "For standard checking accounts, maintain a minimum daily balance of $500 to waive the $12 monthly maintenance fee. For savings accounts, keep a minimum of $300 to avoid the $8 monthly fee. Premium accounts have higher thresholds but more benefits."),
    ("How do I contact customer support?", "You can reach PalBank customer support 24/7 at 1-800-555-0100, via live chat on our website or mobile app, or by emailing support@palbank.com. Branch support is available during business hours."),
    ("Is my money FDIC insured?", "Yes. PalBank is a member of the FDIC. Your deposits are insured up to $250,000 per depositor, per ownership category. This includes checking accounts, savings accounts, CDs, and money market accounts."),
    ("How do I enroll in online banking?", "Visit palbank.com and click 'Enroll in Online Banking'. You'll need your account number, Social Security Number, and the email address associated with your account. You'll receive a verification code by email or SMS to complete enrollment."),
    ("How do I set up account alerts?", "Log in to online banking, go to 'Settings' > 'Alerts & Notifications'. You can set up alerts for low balance, large transactions, deposits, and more. Alerts can be sent via email, SMS, or push notification through our mobile app."),
    ("What should I do if my card is lost or stolen?", "Immediately call 1-800-555-0100 or log in to online banking and select 'Card Services' > 'Report Lost or Stolen Card' to freeze your card instantly. We'll issue a replacement card within 5–7 business days, or 1–2 days for expedited shipping."),
    ("How do I wire money internationally?", "For international wire transfers, visit a branch or call 1-800-555-0100. You'll need the recipient's full name, address, bank name, SWIFT/BIC code, and account number. Fees are $35 for outgoing international wires. Processing takes 1–5 business days."),
    ("What are the CD (Certificate of Deposit) rates?", "Current CD rates vary by term: 3-month at 3.50% APY, 6-month at 4.00% APY, 12-month at 4.25% APY, and 24-month at 4.10% APY. Minimum deposit is $1,000. Early withdrawal penalties may apply. Visit any branch or our website for current rates."),
    ("How do I stop a payment or cancel a check?", "To stop a payment on a check, log in to online banking, go to 'Account Services' > 'Stop Payment', enter the check number and amount, and confirm. A $30 stop payment fee applies. For ACH payments, contact us at least 3 business days before the scheduled payment."),
]

USERS = [
    ("admin",    "admin123",    "Admin User",      "admin@palbank.com",          "admin"),
    ("jsmith",   "password123", "John Smith",       "john.smith@email.com",       "customer"),
    ("mjones",   "password123", "Mary Jones",       "mary.jones@email.com",       "customer"),
    ("bwilliams","password123", "Bob Williams",     "bob.williams@email.com",     "customer"),
    ("sdavis",   "password123", "Sarah Davis",      "sarah.davis@email.com",      "customer"),
    ("cwilson",  "password123", "Charles Wilson",   "charles.wilson@email.com",   "customer"),
    ("ltaylor",  "password123", "Linda Taylor",     "linda.taylor@email.com",     "customer"),
    ("rmartin",  "password123", "Robert Martin",    "robert.martin@email.com",    "customer"),
    ("pthompson","password123", "Patricia Thompson","patricia.thompson@email.com","customer"),
    ("danderson","password123", "David Anderson",   "david.anderson@email.com",   "customer"),
]

DESCRIPTIONS = [
    "Direct Deposit - Payroll", "ATM Withdrawal", "Online Purchase - Amazon",
    "Grocery Store - Whole Foods", "Restaurant - The Bistro", "Gas Station - Shell",
    "Utility Bill - Electric Co", "Netflix Subscription", "Gym Membership",
    "Coffee Shop - Starbucks", "Transfer from Savings", "Transfer to Checking",
    "Insurance Premium", "Mortgage Payment", "Rent Payment", "Phone Bill - AT&T",
    "Internet Service - Comcast", "Uber Ride", "Pharmacy - CVS", "Hardware Store - Home Depot",
    "Airline - Delta", "Hotel - Marriott", "Clothing Store - Gap", "Interest Payment",
    "ATM Fee", "Zelle Transfer", "Check Deposit", "ACH Payment",
]

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def random_date(start_days_ago: int, end_days_ago: int = 0) -> str:
    delta = random.randint(end_days_ago, start_days_ago)
    d = datetime.now() - timedelta(days=delta)
    return d.strftime("%Y-%m-%d %H:%M:%S")

def main():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.executescript("""
        DROP TABLE IF EXISTS transactions;
        DROP TABLE IF EXISTS accounts;
        DROP TABLE IF EXISTS faqs;
        DROP TABLE IF EXISTS users;

        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            role TEXT NOT NULL DEFAULT 'customer',
            created_at TEXT NOT NULL
        );

        CREATE TABLE accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            account_number TEXT UNIQUE NOT NULL,
            account_type TEXT NOT NULL,
            balance REAL NOT NULL DEFAULT 0.0,
            opened_at TEXT NOT NULL
        );

        CREATE TABLE transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER NOT NULL REFERENCES accounts(id),
            date TEXT NOT NULL,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            running_balance REAL NOT NULL
        );

        CREATE TABLE faqs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            answer TEXT NOT NULL
        );
    """)

    # Insert users
    user_ids = {}
    for username, password, full_name, email, role in USERS:
        pw_hash = hash_password(password)
        created = random_date(730, 365)
        c.execute(
            "INSERT INTO users (username, password_hash, full_name, email, role, created_at) VALUES (?,?,?,?,?,?)",
            (username, pw_hash, full_name, email, role, created)
        )
        user_ids[username] = c.lastrowid

    # Insert accounts and transactions for customers only
    account_count = 0
    tx_count = 0
    for username, _, _, _, role in USERS:
        if role != "customer":
            continue
        uid = user_ids[username]
        # Give some users 2 accounts (checking + savings), others just checking
        account_types = ["checking", "savings"] if random.random() > 0.4 else ["checking"]
        for acc_type in account_types:
            acc_num = f"FNB{random.randint(1000000000, 9999999999)}"
            opened = random_date(700, 100)
            starting_balance = round(random.uniform(500, 15000), 2)
            balance = starting_balance
            c.execute(
                "INSERT INTO accounts (user_id, account_number, account_type, balance, opened_at) VALUES (?,?,?,?,?)",
                (uid, acc_num, acc_type, balance, opened)
            )
            acc_id = c.lastrowid
            account_count += 1

            # Generate transactions
            txs = []
            running_bal = starting_balance
            num_txs = random.randint(8, 15)
            for i in range(num_txs, 0, -1):
                desc = random.choice(DESCRIPTIONS)
                if "Deposit" in desc or "Transfer from" in desc or "Payroll" in desc or "Interest" in desc:
                    amount = round(random.uniform(50, 3000), 2)
                else:
                    amount = round(-random.uniform(5, 500), 2)
                running_bal += amount
                txs.append((acc_id, random_date(i * 10, (i - 1) * 10), desc, amount, round(running_bal, 2)))

            # Update final balance to last running_balance
            final_balance = round(running_bal, 2)
            c.execute("UPDATE accounts SET balance=? WHERE id=?", (final_balance, acc_id))

            for tx in txs:
                c.execute(
                    "INSERT INTO transactions (account_id, date, description, amount, running_balance) VALUES (?,?,?,?,?)",
                    tx
                )
                tx_count += 1

    # Insert FAQs
    for question, answer in FAQS:
        c.execute("INSERT INTO faqs (question, answer) VALUES (?,?)", (question, answer))

    conn.commit()
    conn.close()

    print("=== Database Generation Summary ===")
    print(f"Users inserted:        {len(USERS)}")
    print(f"Accounts inserted:     {account_count}")
    print(f"Transactions inserted: {tx_count}")
    print(f"FAQs inserted:         {len(FAQS)}")
    print(f"\nDatabase saved to: {DB_PATH}")
    print("\nTest credentials:")
    print("  admin     / admin123     (role: admin)")
    print("  jsmith    / password123  (role: customer)")
    print("  mjones    / password123  (role: customer)")
    print("  bwilliams / password123  (role: customer)")

if __name__ == "__main__":
    main()
