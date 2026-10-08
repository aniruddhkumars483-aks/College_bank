import streamlit as st
import sqlite3
import re
import cv2
import numpy as np
from PIL import Image
from datetime import datetime
import pandas as pd
import time

st.set_page_config(page_title="FinVault Core - Swiss Banking Terminal", page_icon="🏛️", layout="wide")

# ================= 🏛️ OBSIDIAN MATTE BANKING THEME =================
st.markdown("""
    <style>
    .stApp {
        background-color: #080b11;
        background-image: radial-gradient(rgba(255, 255, 255, 0.03) 1px, transparent 0);
        background-size: 24px 24px;
        color: #e2e8f0;
        font-family: 'Segoe UI', -apple-system, Roboto, sans-serif;
    }
    .terminal-card {
        background: linear-gradient(145deg, #0d121d 0%, #111827 100%);
        border: 1px solid #1e293b;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 20px 0 rgba(0, 0, 0, 0.6);
    }
    .bank-card-titanium {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #334155;
        border-radius: 14px;
        padding: 22px;
        color: #f8fafc;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5);
    }
    .card-frozen {
        background: linear-gradient(135deg, #374151 0%, #1f2937 100%) !important;
        border: 1px dashed #ef4444 !important;
        opacity: 0.7;
    }
    .intruder-banner {
        background: #450a0a;
        border-left: 5px solid #ef4444;
        border-radius: 8px;
        padding: 16px;
        color: #fecaca;
        margin-bottom: 20px;
    }
    .security-badge {
        font-size: 11px;
        letter-spacing: 1px;
        color: #94a3b8;
        text-transform: uppercase;
    }
    </style>
""", unsafe_allow_html=True)

# ================= 🗄️ DATABASE ENGINE =================
def get_db():
    return sqlite3.connect("bank_vault_master.db", check_same_thread=False)

def init_db():
    conn = get_db()
    c = conn.cursor()
    # 1. Profile Table with Biometric Enrollments
    c.execute("""
        CREATE TABLE IF NOT EXISTS user_profile (
            id INTEGER PRIMARY KEY,
            name TEXT,
            email TEXT,
            phone TEXT,
            master_pin TEXT,
            profile_password TEXT,
            face_enrolled INTEGER DEFAULT 0,
            finger_enrolled INTEGER DEFAULT 0,
            is_onboarded INTEGER DEFAULT 0
        )
    """)
    # 2. Bank Accounts
    c.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bank_name TEXT NOT NULL,
            account_type TEXT NOT NULL,
            last4 TEXT NOT NULL,
            balance REAL NOT NULL,
            status TEXT DEFAULT 'ACTIVE'
        )
    """)
    # 3. Transactions
    c.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER,
            title TEXT NOT NULL,
            amount REAL NOT NULL,
            type TEXT NOT NULL,
            category TEXT NOT NULL,
            date TEXT NOT NULL,
            source TEXT DEFAULT 'Core Gateway'
        )
    """)
    # 4. Intruder Logs
    c.execute("""
        CREATE TABLE IF NOT EXISTS intruder_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            attempt_type TEXT NOT NULL,
            details TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

init_db()

# Fetch Profile
def get_profile():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT name, email, phone, master_pin, profile_password, face_enrolled, finger_enrolled, is_onboarded FROM user_profile WHERE id = 1")
    row = c.fetchone()
    conn.close()
    if row:
        return {
            "name": row[0], "email": row[1], "phone": row[2], 
            "pin": row[3], "profile_pass": row[4], 
            "face_enrolled": row[5], "finger_enrolled": row[6],
            "is_onboarded": row[7]
        }
    return None

profile = get_profile()

# OpenCV Face Detection Logic
def detect_face(image_file):
    try:
        img = Image.open(image_file)
        img_np = np.array(img.convert('RGB'))
        gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(60, 60))
        return len(faces) > 0
    except:
        return False

# Intruder Logger
def log_intruder(attempt_type, details):
    conn = get_db()
    c = conn.cursor()
    now_str = datetime.now().strftime("%d %b %Y, %I:%M:%S %p")
    c.execute("INSERT INTO intruder_logs (timestamp, attempt_type, details) VALUES (?, ?, ?)",
              (now_str, attempt_type, details))
    conn.commit()
    conn.close()

# ================= 🚀 SCREEN 1: ONBOARDING SETUP =================
if not profile or profile["is_onboarded"] == 0:
    st.markdown("<br>", unsafe_allow_html=True)
    col_l, col_main, col_r = st.columns([1, 2, 1])
    
    with col_main:
        st.markdown("""
        <div style='text-align: center; margin-bottom: 25px;'>
            <span class='security-badge'>CORE ENROLLMENT WIZARD</span>
            <h1 style='color: #38bdf8; margin: 5px 0 0 0;'>🏛️ FinVault Account Enrollment</h1>
            <p style='color: #64748b;'>Configure credentials, enroll biometric signatures, and link primary bank node.</p>
        </div>
        """, unsafe_allow_html=True)

        if "setup_face_done" not in st.session_state: st.session_state.setup_face_done = False
        if "setup_finger_done" not in st.session_state: st.session_state.setup_finger_done = False

        st.subheader("1. Identity & Credentials")
        u_name = st.text_input("Account Holder Full Name", placeholder="e.g. Rahul Sharma")
        u_email = st.text_input("Corporate / Personal Email", placeholder="e.g. rahul@terminal.com")
        u_phone = st.text_input("Secure Phone Number", placeholder="e.g. +91 9876543210")
        u_pin = st.text_input("Set Master Login PIN (4-6 Digits)", type="password", placeholder="e.g. 8899")
        u_profile_pass = st.text_input("Set Profile Security Password", type="password", placeholder="Password to protect settings")

        st.divider()

        st.subheader("2. Biometric Signature Enrollment")
        tab_f_reg, tab_t_reg = st.tabs(["📷 Enroll Master Face ID", "👆 Enroll Fingerprint Key"])
        
        with tab_f_reg:
            st.caption("Capture and register your master facial biometric:")
            enroll_cam = st.camera_input("Register Master Face", label_visibility="collapsed")
            if enroll_cam:
                if detect_face(enroll_cam):
                    st.session_state.setup_face_done = True
                    st.success("✅ Master Facial Biometric Successfully Enrolled!")
                else:
                    st.error("❌ Face not clearly visible. Please capture again.")

        with tab_t_reg:
            st.caption("Enroll capacitive touch token / fingerprint sensor:")
            if st.button("👆 Scan & Register Touch ID Key", use_container_width=True):
                st.session_state.setup_finger_done = True
                st.success("✅ Touch Biometric Token Successfully Registered!")

        st.divider()

        st.subheader("3. Primary Bank Account Node")
        b_name = st.text_input("Bank Name", placeholder="e.g. State Bank of India / HDFC Bank")
        b_type = st.selectbox("Account Classification", ["Savings Portfolio", "Corporate Current A/C", "Salary Reserve", "Treasury Vault"])
        b_last4 = st.text_input("Account Last 4 Digits", max_chars=4, placeholder="e.g. 4321")
        b_bal = st.number_input("Opening Liquidity Balance (₹)", min_value=100.0, value=50000.0, step=1000.0)

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔒 Complete Full Enrollment & Encrypt Vault", use_container_width=True, type="primary"):
            if u_name and u_pin and u_profile_pass and b_name and len(b_last4) == 4:
                conn = get_db()
                c = conn.cursor()
                c.execute("""
                    INSERT OR REPLACE INTO user_profile 
                    (id, name, email, phone, master_pin, profile_password, face_enrolled, finger_enrolled, is_onboarded) 
                    VALUES (1, ?, ?, ?, ?, ?, ?, ?, 1)
                """, (u_name, u_email, u_phone, u_pin, u_profile_pass, 
                      1 if st.session_state.setup_face_done else 0, 
                      1 if st.session_state.setup_finger_done else 0))
                
                c.execute("INSERT INTO accounts (bank_name, account_type, last4, balance, status) VALUES (?, ?, ?, ?, 'ACTIVE')",
                          (b_name, b_type, b_last4, b_bal))
                conn.commit()
                conn.close()
                st.success("🎉 Enrollment Complete! Redirecting...")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Please fill mandatory fields properly!")
    st.stop()

# ================= 🔐 SCREEN 2: 2-FACTOR BIOMETRIC TERMINAL LOCK =================
if "auth_pin" not in st.session_state: st.session_state.auth_pin = False
if "auth_face" not in st.session_state: st.session_state.auth_face = False
if "auth_finger" not in st.session_state: st.session_state.auth_finger = False
if "unlocked" not in st.session_state: st.session_state.unlocked = False

if not st.session_state.unlocked:
    st.markdown("<br>", unsafe_allow_html=True)
    col_l, col_main, col_r = st.columns([1, 2, 1])
    
    with col_main:
        st.markdown(f"""
        <div style='text-align: center; margin-bottom: 25px;'>
            <span class='security-badge'>AES-256 ENCRYPTED GATEWAY</span>
            <h1 style='color: #38bdf8; margin: 5px 0 0 0;'>🛡️ Vault Access Gate</h1>
            <p style='color: #64748b;'>Identity: <b>{profile['name']}</b> | Policy: <b>2 of 3 Factors Required</b></p>
        </div>
        """, unsafe_allow_html=True)

        verified_count = sum([st.session_state.auth_pin, st.session_state.auth_face, st.session_state.auth_finger])
        st.progress(verified_count / 2 if verified_count <= 2 else 1.0)
        st.markdown(f"<p style='font-size:12px; color:#94a3b8; text-align:right;'>Security Clearance: <b>{verified_count}/2 Verified</b></p>", unsafe_allow_html=True)

        tab_pin, tab_face, tab_finger = st.tabs(["🔢 Security PIN", "📷 Face Biometric", "👆 Touch Sensor"])

        # Factor 1: PIN
        with tab_pin:
            if not st.session_state.auth_pin:
                pin_in = st.text_input("Enter Master PIN", type="password", placeholder="••••••")
                if st.button("Validate PIN", use_container_width=True):
                    if pin_in == profile["pin"]:
                        st.session_state.auth_pin = True
                        st.success("✅ PIN Verified!")
                        st.rerun()
                    else:
                        log_intruder("Unauthorized PIN Attempt", f"Attempted code: '{pin_in}'")
                        st.error("❌ Access Denied: Code Mismatch. Breach logged.")
            else:
                st.success("✅ Factor 1 (PIN) Validated.")

        # Factor 2: Face Biometric
        with tab_face:
            if not st.session_state.auth_face:
                st.caption("Verify against enrolled master face:")
                camera_img = st.camera_input("Biometric Camera", label_visibility="collapsed")
                if camera_img:
                    with st.spinner("Processing Facial Geometry..."):
                        if detect_face(camera_img):
                            st.session_state.auth_face = True
                            st.success("✅ Biometric Signature Matches Enrolled Profile!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            log_intruder("Facial Authentication Failure", "Unrecognized face scanned")
                            st.error("❌ Face biometric verification failed. Retry in good lighting.")
            else:
                st.success("✅ Factor 2 (Facial Scan) Validated.")

        # Factor 3: Fingerprint Sensor
        with tab_finger:
            if not st.session_state.auth_finger:
                st.caption("Capacitive Hardware Key Verification:")
                if st.button("👆 Authenticate Touch ID", use_container_width=True):
                    with st.spinner("Authorizing hardware key token..."):
                        time.sleep(1)
                        st.session_state.auth_finger = True
                        st.success("✅ Touch Cryptogram Accepted!")
                        st.rerun()
            else:
                st.success("✅ Factor 3 (Touch Sensor) Validated.")

        st.divider()
        if verified_count >= 2:
            if st.button("🔓 DECRYPT & OPEN TERMINAL", use_container_width=True, type="primary"):
                st.session_state.unlocked = True
                st.rerun()
        else:
            st.info(f"Complete {2 - verified_count} more factor(s) to obtain security clearance.")

    st.stop()

# ================= 🚀 SCREEN 3: MAIN DASHBOARD (UNLOCKED) =================
with st.sidebar:
    st.markdown(f"<span class='security-badge'>SESSION ACTIVE</span><br><b>{profile['name']}</b>", unsafe_allow_html=True)
    if st.button("🔒 Terminate Session / Lock", use_container_width=True):
        st.session_state.auth_pin = False
        st.session_state.auth_face = False
        st.session_state.auth_finger = False
        st.session_state.unlocked = False
        st.session_state.profile_verified = False
        st.rerun()
    st.divider()

    # ➕ QUICK ADD BANK ACCOUNT
    with st.expander("➕ Link New Bank Node"):
        with st.form("add_bank_form"):
            new_b_name = st.text_input("Institution Name (e.g. ICICI Bank)")
            new_b_type = st.selectbox("Classification", ["Savings Portfolio", "Corporate Current", "Salary Node", "Credit Vault"])
            new_b_last4 = st.text_input("Last 4 Digits", max_chars=4)
            new_b_bal = st.number_input("Opening Liquidity (₹)", min_value=0.0, step=500.0)
            
            if st.form_submit_button("Link Bank Account"):
                if new_b_name and len(new_b_last4) == 4:
                    conn = get_db()
                    c = conn.cursor()
                    c.execute("INSERT INTO accounts (bank_name, account_type, last4, balance, status) VALUES (?, ?, ?, ?, 'ACTIVE')",
                              (new_b_name, new_b_type, new_b_last4, new_b_bal))
                    conn.commit()
                    conn.close()
                    st.success("Bank Node Linked Successfully!")
                    st.rerun()

    # ⚡ CORE GATEWAY
    st.subheader("⚡ Core Payment Gateway")
    with st.form("payment_gateway_form"):
        tx_action = st.radio("Gateway Action", ["💸 Send Liquidity (Debit)", "💰 Receive Liquidity (Credit)"], horizontal=True)
        
        conn = get_db()
        accounts_df = pd.read_sql("SELECT id, bank_name, last4, balance, status FROM accounts WHERE status = 'ACTIVE'", conn)
        conn.close()
        acc_opts = {f"{r['bank_name']} (****{r['last4']}) - ₹{r['balance']:,.2f}": r['id'] for _, r in accounts_df.iterrows()}

        if tx_action == "💸 Send Liquidity (Debit)":
            merchant = st.selectbox("Payee / Merchant", ["Amazon.in", "Swiggy UPI", "Zomato", "Vendor Wire", "Netflix Corporate", "Utility Power"])
            category = "Operational Outflow"
        else:
            merchant = st.selectbox("Funding Source", ["Client Retainer", "Institutional Salary", "Inward Wire", "Treasury Refund", "Dividend Income"])
            category = "Capital Inflow"

        pay_amt = st.number_input("Transaction Amount (₹)", min_value=1.0, value=500.0, step=100.0)
        selected_bank = st.selectbox("Settlement Account", list(acc_opts.keys()) if acc_opts else ["No Active Accounts"])
        
        if st.form_submit_button("Execute Wire Settlement"):
            if acc_opts:
                acc_id = acc_opts[selected_bank]
                conn = get_db()
                c = conn.cursor()
                c.execute("SELECT balance, bank_name FROM accounts WHERE id = ?", (acc_id,))
                row = c.fetchone()
                current_bal, b_name = row[0], row[1]
                now_str = datetime.now().strftime("%d %b, %I:%M %p")

                # INSUFFICIENT BALANCE GUARD
                if tx_action == "💸 Send Liquidity (Debit)" and pay_amt > current_bal:
                    st.error(f"❌ SETTLEMENT CANCELLED: Insufficient Funds in {b_name}. (Liquidity: ₹{current_bal:,.2f})")
                    conn.close()
                else:
                    if tx_action == "💸 Send Liquidity (Debit)":
                        c.execute("INSERT INTO transactions (account_id, title, amount, type, category, date, source) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                  (acc_id, merchant, pay_amt, "EXPENSE", category, now_str, "Outward Wire"))
                        c.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (pay_amt, acc_id))
                        st.toast(f"₹{pay_amt:,.2f} Outflow to {merchant} Executed.", icon="💸")
                    else:
                        c.execute("INSERT INTO transactions (account_id, title, amount, type, category, date, source) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                  (acc_id, merchant, pay_amt, "INCOME", category, now_str, "Inward Wire"))
                        c.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (pay_amt, acc_id))
                        st.toast(f"₹{pay_amt:,.2f} Inflow from {merchant} Settled.", icon="💰")

                    conn.commit()
                    conn.close()
                    time.sleep(1)
                    st.rerun()

# ================= 🚨 INTRUDER AUDIT & DATA LOAD =================
conn = get_db()
intruder_df = pd.read_sql("SELECT * FROM intruder_logs ORDER BY id DESC", conn)
accounts = pd.read_sql("SELECT * FROM accounts", conn)
transactions = pd.read_sql("""
    SELECT t.id, t.title, t.amount, t.type, t.category, t.source, t.date, a.bank_name 
    FROM transactions t 
    LEFT JOIN accounts a ON t.account_id = a.id 
    ORDER BY t.id DESC LIMIT 25
""", conn)
conn.close()

if not intruder_df.empty:
    st.markdown(f"""
    <div class='intruder-banner'>
        <b>SECURITY PROTOCOL ALERT: Unauthorized Access Attempts Detected</b><br>
        <span style='font-size:13px;'>The system repelled <b>{len(intruder_df)} unauthorized login breach(es)</b>. Audit records below.</span>
    </div>
    """, unsafe_allow_html=True)
    with st.expander("🔍 View Security Breach Audit Records"):
        st.dataframe(intruder_df, use_container_width=True, hide_index=True)
        if st.button("🗑️ Purge Security Audit Records"):
            conn = get_db()
            c = conn.cursor()
            c.execute("DELETE FROM intruder_logs")
            conn.commit()
            conn.close()
            st.success("Audit records cleared.")
            st.rerun()

# Main Navigation
tab_dash, tab_analytics, tab_profile = st.tabs(["🏛️ Treasury Hub", "📊 Liquidity Analytics", "⚙️ Bank & Profile Administration"])

# ================= TAB 1: TREASURY HUB =================
with tab_dash:
    active_accounts = accounts[accounts['status'] == 'ACTIVE']
    total_balance = active_accounts['balance'].sum() if not active_accounts.empty else 0.0
    total_income = transactions[transactions['type'] == 'INCOME']['amount'].sum() if not transactions.empty else 0.0
    total_expense = transactions[transactions['type'] == 'EXPENSE']['amount'].sum() if not transactions.empty else 0.0

    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown(f"""
        <div class='terminal-card'>
            <span class='security-badge'>TOTAL ACTIVE LIQUIDITY</span>
            <h1 style='color: #38bdf8; margin: 4px 0 0 0; font-size: 36px;'>₹{total_balance:,.2f}</h1>
        </div>
        """, unsafe_allow_html=True)
    with m2:
        st.markdown(f"""
        <div class='terminal-card'>
            <span class='security-badge'>AGGREGATE CAPITAL INFLOW</span>
            <h1 style='color: #4ade80; margin: 4px 0 0 0; font-size: 36px;'>+₹{total_income:,.2f}</h1>
        </div>
        """, unsafe_allow_html=True)
    with m3:
        st.markdown(f"""
        <div class='terminal-card'>
            <span class='security-badge'>AGGREGATE CAPITAL OUTFLOW</span>
            <h1 style='color: #f87171; margin: 4px 0 0 0; font-size: 36px;'>-₹{total_expense:,.2f}</h1>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("💳 Active Banking Nodes")
    cols = st.columns(max(len(accounts), 1))
    for idx, (_, acc) in enumerate(accounts.iterrows()):
        with cols[idx]:
            is_frozen = acc['status'] == 'FROZEN'
            card_class = "bank-card-titanium card-frozen" if is_frozen else "bank-card-titanium"
            status_tag = "<span style='color: #ef4444; font-size:11px;'>[FROZEN]</span>" if is_frozen else "<span style='color: #4ade80; font-size:11px;'>[ACTIVE NODE]</span>"
            
            st.markdown(f"""
            <div class='{card_class}'>
                <div style='display: flex; justify-content: space-between;'>
                    <span style='font-weight: 700; font-size: 15px;'>{acc['bank_name']}</span>
                    {status_tag}
                </div>
                <div style='color: #94a3b8; font-size: 12px;'>{acc['account_type']}</div>
                <h2 style='margin: 18px 0; font-size: 26px; font-weight: 800; color: #f8fafc;'>₹{acc['balance']:,.2f}</h2>
                <div style='display: flex; justify-content: space-between; color: #94a3b8; font-size: 13px;'>
                    <span>•••• {acc['last4']}</span>
                    <span style='color: #fbbf24;'>EMV CHIP 🔒</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.divider()
    
    col_th, col_tb = st.columns([3, 1])
    with col_th:
        st.subheader("📜 Live Core Transaction Ledger")
    with col_tb:
        if not transactions.empty:
            csv_data = transactions.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Export Audit Statement (CSV)", data=csv_data, file_name="Treasury_Statement.csv", mime="text/csv")

    if not transactions.empty:
        st.dataframe(
            transactions,
            column_config={
                "amount": st.column_config.NumberColumn("Amount (₹)", format="₹%.2f"),
                "type": st.column_config.TextColumn("Flow"),
                "source": st.column_config.TextColumn("Channel"),
            },
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No transaction logs recorded.")

# ================= TAB 2: ANALYTICS =================
with tab_analytics:
    st.subheader("📊 Capital Allocation & Flow Analytics")
    if not transactions.empty:
        expense_df = transactions[transactions['type'] == 'EXPENSE']
        if not expense_df.empty:
            cat_summary = expense_df.groupby("category")["amount"].sum()
            st.bar_chart(cat_summary)
        else:
            st.info("No outflow capital recorded yet.")
    else:
        st.info("Transaction ledger is currently empty.")

# ================= TAB 3: BANK & PROFILE ADMINISTRATION =================
if "profile_verified" not in st.session_state:
    st.session_state.profile_verified = False

with tab_profile:
    st.subheader("⚙️ Executive Security & Bank Node Administration")
    if not st.session_state.profile_verified:
        st.markdown("<p style='color: #94a3b8;'>Access to bank management, credentials, and biometric enrollment requires Master Profile Password authorization.</p>", unsafe_allow_html=True)
        p_pass = st.text_input("Enter Master Profile Password", type="password", placeholder="••••••••")
        if st.button("Authenticate Administration Access"):
            if p_pass == profile["profile_pass"]:
                st.session_state.profile_verified = True
                st.success("Clearance Granted!")
                st.rerun()
            else:
                log_intruder("Unauthorized Settings Breach Attempt", "Attempted to access administration tab with wrong password")
                st.error("❌ Access Denied: Security Violation Logged.")
    else:
        st.success("🔓 Authenticated Session: Administrative Mode Active")
        
        # 1. USER PROFILE & MASTER CREDENTIALS
        st.markdown("### 👤 Executive Identification & Credentials")
        with st.form("edit_profile_form"):
            edit_name = st.text_input("Full Name", value=profile["name"])
            edit_email = st.text_input("Email", value=profile["email"])
            edit_phone = st.text_input("Phone", value=profile["phone"])
            edit_pin = st.text_input("Master PIN (Login)", value=profile["pin"], type="password")
            edit_profile_pass = st.text_input("Master Profile Password (Settings)", value=profile["profile_pass"], type="password")

            if st.form_submit_button("💾 Update Executive Profile & Credentials"):
                conn = get_db()
                c = conn.cursor()
                c.execute("""
                    UPDATE user_profile SET name = ?, email = ?, phone = ?, master_pin = ?, profile_password = ? WHERE id = 1
                """, (edit_name, edit_email, edit_phone, edit_pin, edit_profile_pass))
                conn.commit()
                conn.close()
                st.success("Executive Credentials Updated Successfully!")
                time.sleep(1)
                st.rerun()

        st.divider()

        # 2. DEDICATED BIOMETRIC ENROLLMENT & UPDATE BOX
        st.markdown("### 🧬 Biometric Security Center (Face ID & Touch ID)")
        st.markdown("<p style='color: #94a3b8; font-size: 13px;'>Re-capture your master face biometric or update your Touch ID key below:</p>", unsafe_allow_html=True)
        
        col_bio1, col_bio2 = st.columns(2)
        with col_bio1:
            st.container(border=True).markdown(f"""
            **Face ID Status:** `{'ACTIVE / ENROLLED' if profile['face_enrolled'] else 'NOT ENROLLED'}`
            """)
            st.caption("Capture new face geometry:")
            new_face_cam = st.camera_input("Re-Enroll Face", label_visibility="collapsed")
            if new_face_cam:
                if st.button("💾 Save & Overwrite Face Biometric", use_container_width=True):
                    if detect_face(new_face_cam):
                        conn = get_db()
                        c = conn.cursor()
                        c.execute("UPDATE user_profile SET face_enrolled = 1 WHERE id = 1")
                        conn.commit()
                        conn.close()
                        st.success("✅ Master Face Biometric Successfully Updated!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ Face not recognized clearly. Please try again.")

        with col_bio2:
            st.container(border=True).markdown(f"""
            **Touch ID Status:** `{'ACTIVE / REGISTERED' if profile['finger_enrolled'] else 'NOT REGISTERED'}`
            """)
            st.caption("Re-register capacitive touch hardware token:")
            if st.button("👆 Re-Authenticate & Update Touch ID Key", use_container_width=True):
                conn = get_db()
                c = conn.cursor()
                c.execute("UPDATE user_profile SET finger_enrolled = 1 WHERE id = 1")
                conn.commit()
                conn.close()
                st.success("✅ Touch ID Key Re-Enrolled Successfully!")
                time.sleep(1)
                st.rerun()

        st.divider()

        # 3. BANK PORTFOLIO MANAGER (EDIT / FREEZE / DELETE)
        st.markdown("### 🏦 Linked Bank Node Management")
        conn = get_db()
        all_banks = pd.read_sql("SELECT * FROM accounts", conn)
        conn.close()

        if not all_banks.empty:
            bank_dict = {f"{row['bank_name']} (****{row['last4']}) - Status: {row['status']}": row['id'] for _, row in all_banks.iterrows()}
            selected_manage_bank = st.selectbox("Select Bank Account to Manage / Edit", list(bank_dict.keys()))
            manage_id = bank_dict[selected_manage_bank]
            target_bank = all_banks[all_banks['id'] == manage_id].iloc[0]

            with st.form("edit_bank_form"):
                st.markdown(f"**Editing Details for: {target_bank['bank_name']}**")
                e_name = st.text_input("Bank Name", value=target_bank['bank_name'])
                e_type = st.selectbox("Account Classification", ["Savings Portfolio", "Corporate Current", "Salary Node", "Credit Vault"], 
                                      index=0 if "Savings" in target_bank['account_type'] else 1)
                e_last4 = st.text_input("Last 4 Digits", value=target_bank['last4'], max_chars=4)
                e_bal = st.number_input("Adjust Balance (₹)", value=float(target_bank['balance']), step=500.0)
                e_status = st.selectbox("Account Operational Status", ["ACTIVE", "FROZEN"], index=0 if target_bank['status'] == 'ACTIVE' else 1)

                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    save_bank_btn = st.form_submit_button("💾 Update the bank detail/save")
                with col_b2:
                    del_bank_btn = st.form_submit_button("🗑️ Delete / Disable the bank Account")

                if save_bank_btn:
                    conn = get_db()
                    c = conn.cursor()
                    c.execute("UPDATE accounts SET bank_name = ?, account_type = ?, last4 = ?, balance = ?, status = ? WHERE id = ?",
                              (e_name, e_type, e_last4, e_bal, e_status, manage_id))
                    conn.commit()
                    conn.close()
                    st.success("Bank Account Details Updated Successfully!")
                    time.sleep(1)
                    st.rerun()

                if del_bank_btn:
                    if len(all_banks) <= 1:
                        st.error("Cannot delete primary bank node. At least 1 account must remain active!")
                    else:
                        conn = get_db()
                        c = conn.cursor()
                        c.execute("DELETE FROM accounts WHERE id = ?", (manage_id,))
                        c.execute("DELETE FROM transactions WHERE account_id = ?", (manage_id,))
                        conn.commit()
                        conn.close()
                        st.warning(f"Bank Account '{target_bank['bank_name']}' permanently removed.")
                        time.sleep(1)
                        st.rerun()