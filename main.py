import streamlit as st
import sqlite3
import cv2
import numpy as np
from PIL import Image
from datetime import datetime
import pandas as pd
import time

st.set_page_config(page_title="FinVault Core - Multi-User Banking", page_icon="🏛️", layout="wide")

# ================= 🎨 ULTRA FAST MOBILE-OPTIMIZED THEME =================
st.markdown("""
    <style>
    .stApp {
        background-color: #080b11;
        color: #e2e8f0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    .bank-card-titanium {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 18px;
        color: #f8fafc;
        margin-bottom: 10px;
    }
    .card-frozen {
        border: 1px dashed #ef4444 !important;
        opacity: 0.6;
    }
    .terminal-card {
        background: #0d121d;
        border: 1px solid #1e293b;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 12px;
    }
    .intruder-banner {
        background: #450a0a;
        border-left: 4px solid #ef4444;
        border-radius: 6px;
        padding: 12px;
        color: #fecaca;
        margin-bottom: 15px;
    }
    </style>
""", unsafe_allow_html=True)

# ================= 🗄️ DATABASE (MULTI-USER ENGINE) =================
def get_db():
    return sqlite3.connect("bank_vault_multiuser.db", check_same_thread=False)

def init_db():
    conn = get_db()
    c = conn.cursor()
    # 1. Multi-User Table (Unique username per person)
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            master_pin TEXT NOT NULL,
            profile_password TEXT NOT NULL,
            face_enrolled INTEGER DEFAULT 0,
            finger_enrolled INTEGER DEFAULT 0
        )
    """)
    # 2. Bank Accounts (Linked to specific user_id)
    c.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            bank_name TEXT NOT NULL,
            account_type TEXT NOT NULL,
            last4 TEXT NOT NULL,
            balance REAL NOT NULL,
            status TEXT DEFAULT 'ACTIVE',
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    # 3. Transactions (Linked to specific user_id)
    c.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            account_id INTEGER,
            title TEXT NOT NULL,
            amount REAL NOT NULL,
            type TEXT NOT NULL,
            category TEXT NOT NULL,
            date TEXT NOT NULL,
            source TEXT DEFAULT 'Core Gateway',
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    # 4. Intruder Logs (Linked to attempted username)
    c.execute("""
        CREATE TABLE IF NOT EXISTS intruder_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            timestamp TEXT NOT NULL,
            attempt_type TEXT NOT NULL,
            details TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

init_db()

# Face Detection Helper
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

# ================= 🔐 SESSION STATE =================
if "logged_user_id" not in st.session_state: st.session_state.logged_user_id = None
if "auth_pin" not in st.session_state: st.session_state.auth_pin = False
if "auth_face" not in st.session_state: st.session_state.auth_face = False
if "auth_finger" not in st.session_state: st.session_state.auth_finger = False
if "profile_verified" not in st.session_state: st.session_state.profile_verified = False

# ================= 🚪 SCREEN 1: LOGIN & SIGN UP (MULTI-USER GATE) =================
if st.session_state.logged_user_id is None:
    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    
    with c2:
        st.markdown("""
        <div style='text-align: center; margin-bottom: 20px;'>
            <h1 style='color: #38bdf8; margin: 0;'>🏛️ FinVault Core Terminal</h1>
            <p style='color: #64748b;'>Multi-User Confidential Treasury & Bank Account Vault</p>
        </div>
        """, unsafe_allow_html=True)

        auth_mode = st.radio("Choose Action", ["🔑 Login Existing Vault", "📝 Create New Account"], horizontal=True)

        # TAB A: LOGIN
        if auth_mode == "🔑 Login Existing Vault":
            login_user = st.text_input("Username / Account ID", placeholder="e.g. rahul123").strip().lower()
            
            if login_user:
                conn = get_db()
                c = conn.cursor()
                c.execute("SELECT id, name, master_pin, face_enrolled, finger_enrolled FROM users WHERE username = ?", (login_user,))
                user_record = c.fetchone()
                conn.close()

                if user_record:
                    u_id, u_name, u_pin, has_face, has_finger = user_record
                    st.info(f"Identity Verified: **{u_name}**. Complete 2 of 3 Factors to Decrypt.")

                    # Multi-Factor Verification
                    verified_count = sum([st.session_state.auth_pin, st.session_state.auth_face, st.session_state.auth_finger])
                    st.progress(verified_count / 2 if verified_count <= 2 else 1.0)
                    st.caption(f"Security Clearance: **{verified_count}/2 Verified**")

                    f_pin, f_face, f_touch = st.tabs(["🔢 PIN", "📷 Face ID", "👆 Touch Key"])
                    
                    with f_pin:
                        if not st.session_state.auth_pin:
                            p_in = st.text_input("Master PIN", type="password", key="login_pin")
                            if st.button("Validate PIN"):
                                if p_in == u_pin:
                                    st.session_state.auth_pin = True
                                    st.success("✅ PIN Validated!")
                                    st.rerun()
                                else:
                                    # Log Intruder
                                    conn = get_db()
                                    c = conn.cursor()
                                    now = datetime.now().strftime("%d %b %Y, %I:%M:%S %p")
                                    c.execute("INSERT INTO intruder_logs (user_id, timestamp, attempt_type, details) VALUES (?, ?, ?, ?)",
                                              (u_id, now, "Wrong PIN", f"Failed code: {p_in}"))
                                    conn.commit()
                                    conn.close()
                                    st.error("❌ Wrong PIN! Security breach logged.")
                        else:
                            st.success("✅ PIN Verified")

                    with f_face:
                        if not st.session_state.auth_face:
                            cam_feed = st.camera_input("Scan Face", label_visibility="collapsed")
                            if cam_feed and detect_face(cam_feed):
                                st.session_state.auth_face = True
                                st.success("✅ Face Biometric Verified!")
                                time.sleep(1)
                                st.rerun()
                        else:
                            st.success("✅ Face Verified")

                    with f_touch:
                        if not st.session_state.auth_finger:
                            if st.button("👆 Authenticate Touch Token", use_container_width=True):
                                st.session_state.auth_finger = True
                                st.success("✅ Touch Token Accepted!")
                                st.rerun()
                        else:
                            st.success("✅ Touch Verified")

                    st.divider()
                    if verified_count >= 2:
                        if st.button("🔓 DECRYPT & OPEN VAULT", use_container_width=True, type="primary"):
                            st.session_state.logged_user_id = u_id
                            st.session_state.auth_pin = False
                            st.session_state.auth_face = False
                            st.session_state.auth_finger = False
                            st.rerun()
                else:
                    st.warning("Username not found. Please click 'Create New Account' to register!")

        # TAB B: REGISTER NEW USER
        else:
            st.subheader("Register Your Private Vault")
            with st.form("reg_form"):
                new_username = st.text_input("Choose Username (Must be unique)", placeholder="e.g. rahul123").strip().lower()
                new_name = st.text_input("Full Name", placeholder="Rahul Sharma")
                new_phone = st.text_input("Phone Number")
                new_pin = st.text_input("Set Master Login PIN (4-6 Digits)", type="password")
                new_profile_pass = st.text_input("Set Settings/Profile Protection Password", type="password")

                st.markdown("#### Initial Bank Account Node")
                init_b_name = st.text_input("Bank Name", placeholder="e.g. HDFC Bank")
                init_b_type = st.selectbox("Classification", ["Savings Portfolio", "Salary Reserve", "Corporate Current", "Credit Vault"])
                init_b_last4 = st.text_input("Last 4 Digits", max_chars=4, placeholder="1234")
                init_b_bal = st.number_input("Opening Balance (₹)", min_value=100.0, value=25000.0, step=500.0)

                if st.form_submit_button("🚀 Create Vault & Register", use_container_width=True):
                    if new_username and new_name and new_pin and new_profile_pass and init_b_name and len(init_b_last4) == 4:
                        try:
                            conn = get_db()
                            c = conn.cursor()
                            c.execute("""
                                INSERT INTO users (username, name, phone, master_pin, profile_password, face_enrolled, finger_enrolled) 
                                VALUES (?, ?, ?, ?, ?, 1, 1)
                            """, (new_username, new_name, new_phone, new_pin, new_profile_pass))
                            user_new_id = c.lastrowid
                            
                            c.execute("INSERT INTO accounts (user_id, bank_name, account_type, last4, balance, status) VALUES (?, ?, ?, ?, ?, 'ACTIVE')",
                                      (user_new_id, init_b_name, init_b_type, init_b_last4, init_b_bal))
                            conn.commit()
                            conn.close()
                            st.success("🎉 Account Created Successfully! Now select 'Login Existing Vault' to login.")
                        except sqlite3.IntegrityError:
                            st.error("❌ This username is already taken! Please choose another one.")
                    else:
                        st.error("Please fill all fields properly!")
    st.stop()

# ================= 🚀 SCREEN 2: LOGGED IN USER DASHBOARD =================
USER_ID = st.session_state.logged_user_id

# Fetch Current Logged-in User Info
conn = get_db()
c = conn.cursor()
c.execute("SELECT username, name, email, phone, master_pin, profile_password, face_enrolled, finger_enrolled FROM users WHERE id = ?", (USER_ID,))
user_data = c.fetchone()
conn.close()

user_dict = {
    "username": user_data[0], "name": user_data[1], "email": user_data[2], 
    "phone": user_data[3], "pin": user_data[4], "profile_pass": user_data[5],
    "face_enrolled": user_data[6], "finger_enrolled": user_data[7]
}

# Sidebar
with st.sidebar:
    st.markdown(f"**👤 Active Vault:** {user_dict['name']} (`{user_dict['username']}`)")
    if st.button("🔒 Logout / Switch Account", use_container_width=True):
        st.session_state.logged_user_id = None
        st.session_state.auth_pin = False
        st.session_state.auth_face = False
        st.session_state.auth_finger = False
        st.session_state.profile_verified = False
        st.rerun()
    st.divider()

    # Quick Add Bank
    with st.expander("➕ Link New Bank Node"):
        with st.form("quick_add_b"):
            qb_name = st.text_input("Bank Name (e.g. SBI)")
            qb_type = st.selectbox("Type", ["Savings Portfolio", "Salary Reserve", "Corporate Current", "Credit Vault"])
            qb_last4 = st.text_input("Last 4 Digits", max_chars=4)
            qb_bal = st.number_input("Opening Balance (₹)", min_value=0.0, step=500.0)
            if st.form_submit_button("Link Node"):
                if qb_name and len(qb_last4) == 4:
                    conn = get_db()
                    c = conn.cursor()
                    c.execute("INSERT INTO accounts (user_id, bank_name, account_type, last4, balance, status) VALUES (?, ?, ?, ?, ?, 'ACTIVE')",
                              (USER_ID, qb_name, qb_type, qb_last4, qb_bal))
                    conn.commit()
                    conn.close()
                    st.success("Bank linked!")
                    st.rerun()

    # Core Payment Gateway Simulator
    st.subheader("⚡ Wire Gateway")
    with st.form("gw_form"):
        tx_action = st.radio("Action", ["💸 Pay (Debit)", "💰 Receive (Credit)"], horizontal=True)
        
        conn = get_db()
        accs = pd.read_sql("SELECT id, bank_name, last4, balance FROM accounts WHERE user_id = ? AND status = 'ACTIVE'", conn, params=(USER_ID,))
        conn.close()
        acc_opts = {f"{r['bank_name']} (****{r['last4']}) - ₹{r['balance']:,.2f}": r['id'] for _, r in accs.iterrows()}

        merchant = st.text_input("Payee / Source", value="Amazon UPI" if "Pay" in tx_action else "Client Payment")
        amt = st.number_input("Amount (₹)", min_value=1.0, value=500.0, step=100.0)
        chosen_acc = st.selectbox("Account Node", list(acc_opts.keys()) if acc_opts else ["No Active Accounts"])

        if st.form_submit_button("Execute Wire"):
            if acc_opts:
                t_acc_id = acc_opts[chosen_acc]
                conn = get_db()
                c = conn.cursor()
                c.execute("SELECT balance, bank_name FROM accounts WHERE id = ?", (t_acc_id,))
                c_bal, b_title = c.fetchone()
                now_str = datetime.now().strftime("%d %b, %I:%M %p")

                # INSUFFICIENT BALANCE GUARD
                if "Pay" in tx_action and amt > c_bal:
                    st.error(f"❌ CANCELLED: Insufficient Funds in {b_title}. (Bal: ₹{c_bal:,.2f})")
                    conn.close()
                else:
                    if "Pay" in tx_action:
                        c.execute("INSERT INTO transactions (user_id, account_id, title, amount, type, category, date, source) VALUES (?, ?, ?, ?, 'EXPENSE', 'Online Outflow', ?, 'Wire Gateway')",
                                  (USER_ID, t_acc_id, merchant, amt, now_str))
                        c.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amt, t_acc_id))
                        st.toast(f"₹{amt:,.2f} Paid successfully!", icon="💸")
                    else:
                        c.execute("INSERT INTO transactions (user_id, account_id, title, amount, type, category, date, source) VALUES (?, ?, ?, ?, 'INCOME', 'Capital Inflow', ?, 'Wire Gateway')",
                                  (USER_ID, t_acc_id, merchant, amt, now_str))
                        c.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amt, t_acc_id))
                        st.toast(f"₹{amt:,.2f} Received successfully!", icon="💰")
                    conn.commit()
                    conn.close()
                    time.sleep(1)
                    st.rerun()

# Check Intruder Logs for this user
conn = get_db()
intruders = pd.read_sql("SELECT * FROM intruder_logs WHERE user_id = ? ORDER BY id DESC", conn, params=(USER_ID,))
accounts = pd.read_sql("SELECT * FROM accounts WHERE user_id = ?", conn, params=(USER_ID,))
transactions = pd.read_sql("""
    SELECT t.id, t.title, t.amount, t.type, t.category, t.source, t.date, a.bank_name 
    FROM transactions t 
    LEFT JOIN accounts a ON t.account_id = a.id 
    WHERE t.user_id = ? 
    ORDER BY t.id DESC LIMIT 20
""", conn, params=(USER_ID,))
conn.close()

if not intruders.empty:
    st.markdown(f"""
    <div class='intruder-banner'>
        <b>🚨 SECURITY WARNING: Unauthorized Attempts Detected!</b><br>
        <span style='font-size:12px;'>Someone attempted to breach your vault <b>{len(intruders)} time(s)</b>. Check audit logs below.</span>
    </div>
    """, unsafe_allow_html=True)
    with st.expander("🔍 View Intruder Audit Logs"):
        st.dataframe(intruders, use_container_width=True, hide_index=True)
        if st.button("🗑️ Clear Breach Logs"):
            conn = get_db()
            c = conn.cursor()
            c.execute("DELETE FROM intruder_logs WHERE user_id = ?", (USER_ID,))
            conn.commit()
            conn.close()
            st.rerun()

# ================= 📱 MOBILE-OPTIMIZED TOP MENU =================
menu_choice = st.radio("Navigation Menu", ["🏛️ Treasury Dashboard", "📊 Spending Analytics", "⚙️ Profile & Bank Administration"], horizontal=True)

# 1. TREASURY DASHBOARD
if menu_choice == "🏛️ Treasury Dashboard":
    active_accs = accounts[accounts['status'] == 'ACTIVE']
    total_bal = active_accs['balance'].sum() if not active_accs.empty else 0.0
    tot_inc = transactions[transactions['type'] == 'INCOME']['amount'].sum() if not transactions.empty else 0.0
    tot_exp = transactions[transactions['type'] == 'EXPENSE']['amount'].sum() if not transactions.empty else 0.0

    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown(f"<div class='terminal-card'><span style='color:#94a3b8;font-size:11px;'>ACTIVE LIQUIDITY</span><h2 style='color:#38bdf8;margin:2px 0;'>₹{total_bal:,.2f}</h2></div>", unsafe_allow_html=True)
    with m2:
        st.markdown(f"<div class='terminal-card'><span style='color:#94a3b8;font-size:11px;'>TOTAL INFLOW</span><h2 style='color:#4ade80;margin:2px 0;'>+₹{tot_inc:,.2f}</h2></div>", unsafe_allow_html=True)
    with m3:
        st.markdown(f"<div class='terminal-card'><span style='color:#94a3b8;font-size:11px;'>TOTAL OUTFLOW</span><h2 style='color:#f87171;margin:2px 0;'>-₹{tot_exp:,.2f}</h2></div>", unsafe_allow_html=True)

    st.subheader("💳 Active Banking Nodes")
    if not accounts.empty:
        cols = st.columns(max(len(accounts), 1))
        for idx, (_, acc) in enumerate(accounts.iterrows()):
            with cols[idx]:
                is_froz = acc['status'] == 'FROZEN'
                card_cls = "bank-card-titanium card-frozen" if is_froz else "bank-card-titanium"
                status_txt = "<span style='color:#ef4444;font-size:11px;'>[FROZEN]</span>" if is_froz else "<span style='color:#4ade80;font-size:11px;'>[ACTIVE]</span>"
                st.markdown(f"""
                <div class='{card_cls}'>
                    <div style='display:flex;justify-content:space-between;'>
                        <b>{acc['bank_name']}</b> {status_txt}
                    </div>
                    <div style='color:#94a3b8;font-size:12px;'>{acc['account_type']}</div>
                    <h3 style='margin:12px 0;color:#f8fafc;'>₹{acc['balance']:,.2f}</h3>
                    <div style='display:flex;justify-content:space-between;color:#94a3b8;font-size:12px;'>
                        <span>•••• {acc['last4']}</span> <span style='color:#fbbf24;'>EMV 🔒</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

    st.divider()
    c_th, c_tb = st.columns([3, 1])
    with c_th: st.subheader("📜 Live Ledger")
    with c_tb:
        if not transactions.empty:
            st.download_button("📥 Export CSV", data=transactions.to_csv(index=False).encode('utf-8'), file_name="Statement.csv", mime="text/csv")
    
    if not transactions.empty:
        st.dataframe(transactions, use_container_width=True, hide_index=True)
    else:
        st.info("No transaction records found.")

# 2. SPENDING ANALYTICS
elif menu_choice == "📊 Spending Analytics":
    st.subheader("📊 Expense Allocation by Category")
    if not transactions.empty:
        exp_df = transactions[transactions['type'] == 'EXPENSE']
        if not exp_df.empty:
            cat_sum = exp_df.groupby("category")["amount"].sum()
            st.bar_chart(cat_sum)
        else:
            st.info("No expense data available for charts.")
    else:
        st.info("Ledger is currently empty.")

# 3. PROFILE & BANK ADMINISTRATION (DOUBLE-LOCKED)
elif menu_choice == "⚙️ Profile & Bank Administration":
    st.subheader("⚙️ Executive Administration & Node Manager")
    
    if not st.session_state.profile_verified:
        st.info("🔒 Enter your Master Profile Password to unlock this confidential administration panel.")
        p_check = st.text_input("Enter Profile Password", type="password")
        if st.button("Authenticate Administration Access"):
            if p_check == user_dict["profile_pass"]:
                st.session_state.profile_verified = True
                st.success("Access Granted!")
                st.rerun()
            else:
                st.error("❌ Wrong Profile Password!")
    else:
        st.success("🔓 Administrative Access Granted")

        # 1. Profile Details
        st.markdown("### 👤 Update Credentials")
        with st.form("upd_prof_f"):
            up_name = st.text_input("Full Name", value=user_dict["name"])
            up_phone = st.text_input("Phone Number", value=user_dict["phone"] or "")
            up_pin = st.text_input("Master PIN", value=user_dict["pin"], type="password")
            up_ppass = st.text_input("Profile Password", value=user_dict["profile_pass"], type="password")

            if st.form_submit_button("💾 Save Profile Changes"):
                conn = get_db()
                c = conn.cursor()
                c.execute("UPDATE users SET name = ?, phone = ?, master_pin = ?, profile_password = ? WHERE id = ?",
                          (up_name, up_phone, up_pin, up_ppass, USER_ID))
                conn.commit()
                conn.close()
                st.success("Credentials updated!")
                time.sleep(1)
                st.rerun()

        st.divider()

        # 2. Bank Management (Edit / Freeze / Delete)
        st.markdown("### 🏦 Manage Your Linked Bank Accounts")
        if not accounts.empty:
            b_choices = {f"{r['bank_name']} (****{r['last4']}) - Status: {r['status']}": r['id'] for _, r in accounts.iterrows()}
            selected_b_str = st.selectbox("Select Account to Manage", list(b_choices.keys()))
            sel_b_id = b_choices[selected_b_str]
            b_info = accounts[accounts['id'] == sel_b_id].iloc[0]

            with st.form("mng_b_form"):
                eb_name = st.text_input("Bank Name", value=b_info['bank_name'])
                eb_type = st.selectbox("Type", ["Savings Portfolio", "Salary Reserve", "Corporate Current", "Credit Vault"],
                                       index=0 if "Savings" in b_info['account_type'] else 1)
                eb_last4 = st.text_input("Last 4 Digits", value=b_info['last4'], max_chars=4)
                eb_bal = st.number_input("Adjust Balance (₹)", value=float(b_info['balance']), step=500.0)
                eb_status = st.selectbox("Status", ["ACTIVE", "FROZEN"], index=0 if b_info['status'] == 'ACTIVE' else 1)

                cb1, cb2 = st.columns(2)
                with cb1: save_b = st.form_submit_button("💾 Save Bank Changes")
                with cb2: del_b = st.form_submit_button("🗑️ Delete Bank Account")

                if save_b:
                    conn = get_db()
                    c = conn.cursor()
                    c.execute("UPDATE accounts SET bank_name = ?, account_type = ?, last4 = ?, balance = ?, status = ? WHERE id = ? AND user_id = ?",
                              (eb_name, eb_type, eb_last4, eb_bal, eb_status, sel_b_id, USER_ID))
                    conn.commit()
                    conn.close()
                    st.success("Bank details updated!")
                    time.sleep(1)
                    st.rerun()

                if del_b:
                    if len(accounts) <= 1:
                        st.error("Cannot delete your only primary bank account!")
                    else:
                        conn = get_db()
                        c = conn.cursor()
                        c.execute("DELETE FROM accounts WHERE id = ? AND user_id = ?", (sel_b_id, USER_ID))
                        c.execute("DELETE FROM transactions WHERE account_id = ? AND user_id = ?", (sel_b_id, USER_ID))
                        conn.commit()
                        conn.close()
                        st.warning("Bank Account removed.")
                        time.sleep(1)
                        st.rerun()
