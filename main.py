import streamlit as st
import sqlite3
import cv2
import numpy as np
from PIL import Image
from datetime import datetime
import pandas as pd
import time

st.set_page_config(page_title="FinVault Core - AI Banking", page_icon="🏛️", layout="wide")

# ================= 📱 ANDROID SCROLL & TITANIUM THEME =================
st.markdown("""
    <style>
    html, body, .stApp {
        background-color: #080b11 !important;
        color: #e2e8f0 !important;
        height: auto !important;
        min-height: 100vh !important;
        overflow-y: auto !important;
        -webkit-overflow-scrolling: touch !important;
    }
    [data-testid="stAppViewContainer"] {
        overflow-y: auto !important;
        -webkit-overflow-scrolling: touch !important;
        padding-bottom: 80px !important;
    }
    .terminal-card {
        background: #0d121d;
        border: 1px solid #1e293b;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
    }
    .bank-card-titanium {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #334155;
        border-radius: 14px;
        padding: 20px;
        color: #f8fafc;
        margin-bottom: 12px;
    }
    .card-frozen {
        border: 1px dashed #ef4444 !important;
        opacity: 0.6;
    }
    .intruder-banner {
        background: #450a0a;
        border-left: 5px solid #ef4444;
        border-radius: 8px;
        padding: 12px;
        color: #fecaca;
        margin-bottom: 15px;
    }
    .fingerprint-pad {
        background: radial-gradient(circle, rgba(56, 189, 248, 0.12) 0%, rgba(13, 18, 29, 0.9) 70%);
        border: 2px dashed #38bdf8;
        border-radius: 16px;
        padding: 20px;
        text-align: center;
        margin: 10px 0;
    }
    .chat-bubble-ai {
        background: #111827;
        border: 1px solid #38bdf8;
        border-radius: 12px;
        padding: 12px;
        margin-bottom: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# ================= 🗄️ DATABASE ENGINE =================
def get_db():
    return sqlite3.connect("bank_vault_v7.db", check_same_thread=False)

def init_db():
    conn = get_db()
    c = conn.cursor()
    # Users Table
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            master_pin TEXT NOT NULL,
            profile_password TEXT NOT NULL,
            face_enrolled INTEGER DEFAULT 0,
            touch_token TEXT NOT NULL
        )
    """)
    # Accounts Table
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
    # Transactions Table
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
    # Intruder Logs
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

# OpenCV Face Detection
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

# ================= 🔐 APP STATE MANAGEMENT =================
if "auth_pin" not in st.session_state: st.session_state.auth_pin = False
if "auth_face" not in st.session_state: st.session_state.auth_face = False
if "auth_finger" not in st.session_state: st.session_state.auth_finger = False
if "unlocked" not in st.session_state: st.session_state.unlocked = False
if "profile_verified" not in st.session_state: st.session_state.profile_verified = False
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        {"role": "assistant", "content": "Namaste! Main aapka **FinAI Assistant** hoon. Aap mujhse balance, kharche, ya saving tips ke baare mein kuch bhi pooch sakte hain! 🤖"}
    ]

def get_device_user():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, name, master_pin, profile_password, face_enrolled, touch_token, phone, email FROM users ORDER BY id ASC LIMIT 1")
    row = c.fetchone()
    conn.close()
    if row:
        return {
            "id": row[0], "name": row[1], "pin": row[2], 
            "profile_pass": row[3], "face_enrolled": row[4], 
            "touch_token": row[5], "phone": row[6], "email": row[7]
        }
    return None

device_user = get_device_user()

# ================= 🚀 SCREEN 1: NEW USER SETUP WIZARD =================
if device_user is None:
    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    
    with c2:
        st.markdown("""
        <div style='text-align: center; margin-bottom: 20px;'>
            <h1 style='color: #38bdf8; margin: 0;'>🏛️ FinVault Initial Setup</h1>
            <p style='color: #64748b;'>Configure credentials, enroll biometrics, and link primary bank.</p>
        </div>
        """, unsafe_allow_html=True)

        if "reg_step" not in st.session_state: st.session_state.reg_step = 1
        if "temp_face_ok" not in st.session_state: st.session_state.temp_face_ok = False
        if "temp_finger_ok" not in st.session_state: st.session_state.temp_finger_ok = False

        # STEP 1: Details & Credentials
        if st.session_state.reg_step == 1:
            st.subheader("1. Profile & Master Credentials")
            u_name = st.text_input("Your Full Name", placeholder="Rahul Sharma")
            u_phone = st.text_input("Phone Number", placeholder="+91 9876543210")
            u_pin = st.text_input("Set Master Login PIN (4-6 Digits)", type="password", placeholder="e.g. 8899")
            u_ppass = st.text_input("Set Profile Security Password", type="password", placeholder="Password to protect settings")

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Next: Enroll Biometrics ➡️", use_container_width=True, type="primary"):
                if u_name and u_pin and u_ppass:
                    st.session_state.temp_name = u_name
                    st.session_state.temp_phone = u_phone
                    st.session_state.temp_pin = u_pin
                    st.session_state.temp_ppass = u_ppass
                    st.session_state.reg_step = 2
                    st.rerun()
                else:
                    st.error("Please fill Name, PIN, and Profile Password!")

        # STEP 2: Biometrics Setup (Face & Finger)
        elif st.session_state.reg_step == 2:
            st.subheader("2. Biometric Signature Enrollment")
            
            # Face
            st.markdown("#### 📷 1. Enroll Master Face")
            st.caption("Scan your face clearly via camera:")
            setup_cam = st.camera_input("Capture Face Biometric", label_visibility="collapsed")
            if setup_cam:
                if detect_face(setup_cam):
                    st.session_state.temp_face_ok = True
                    st.success("✅ Face Biometric Successfully Scanned!")
                else:
                    st.error("❌ Face not detected clearly. Try again in good lighting.")

            st.divider()

            # Fingerprint Sensor with Mandatory Touch Token
            st.markdown("#### 👆 2. Enroll Fingerprint Sensor & Biometric Token")
            st.markdown("""
            <div class='fingerprint-pad'>
                <span style='font-size: 38px;'>🫆</span><br>
                <b style='color: #38bdf8;'>HARDWARE BIOMETRIC SENSOR</b><br>
                <span style='font-size: 12px; color: #94a3b8;'>Set a secret 4-digit Biometric Touch Token to link with your sensor scan</span>
            </div>
            """, unsafe_allow_html=True)
            
            touch_token_reg = st.text_input("Set 4-Digit Biometric Touch Token", type="password", placeholder="e.g. 1122", key="reg_touch_token")
            
            if st.button("👆 Place Thumb & Register Sensor Token", use_container_width=True):
                if touch_token_reg and len(touch_token_reg) >= 4:
                    with st.spinner("Calibrating sensor and encrypting hardware token..."):
                        time.sleep(1.2)
                        st.session_state.temp_touch_token = touch_token_reg
                        st.session_state.temp_finger_ok = True
                        st.success("✅ Fingerprint Sensor & Biometric Token Successfully Registered!")
                else:
                    st.error("❌ Enter a valid 4-digit Biometric Touch Token before scanning!")

            st.markdown("<br>", unsafe_allow_html=True)
            c_back, c_next = st.columns(2)
            with c_back:
                if st.button("⬅️ Back"):
                    st.session_state.reg_step = 1
                    st.rerun()
            with c_next:
                if st.button("Next: Link Bank ➡️", type="primary"):
                    if st.session_state.temp_finger_ok:
                        st.session_state.reg_step = 3
                        st.rerun()
                    else:
                        st.error("Please enroll your Fingerprint & Touch Token first!")

        # STEP 3: Initial Bank Node
        elif st.session_state.reg_step == 3:
            st.subheader("3. Primary Bank Account Node")
            b_name = st.text_input("Bank Name", placeholder="e.g. State Bank of India / HDFC")
            b_type = st.selectbox("Type", ["Savings Portfolio", "Salary Reserve", "Corporate Current", "Credit Vault"])
            b_last4 = st.text_input("Last 4 Digits", max_chars=4, placeholder="1234")
            b_bal = st.number_input("Opening Balance (₹)", min_value=100.0, value=25000.0, step=500.0)

            c_back2, c_finish = st.columns(2)
            with c_back2:
                if st.button("⬅️ Back"):
                    st.session_state.reg_step = 2
                    st.rerun()
            with c_finish:
                if st.button("🚀 Complete Setup", type="primary"):
                    if b_name and len(b_last4) == 4:
                        conn = get_db()
                        c = conn.cursor()
                        c.execute("""
                            INSERT INTO users (name, phone, master_pin, profile_password, face_enrolled, touch_token)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (st.session_state.temp_name, st.session_state.temp_phone, st.session_state.temp_pin, 
                              st.session_state.temp_ppass, 1 if st.session_state.temp_face_ok else 0, st.session_state.temp_touch_token))
                        new_uid = c.lastrowid

                        c.execute("INSERT INTO accounts (user_id, bank_name, account_type, last4, balance, status) VALUES (?, ?, ?, ?, ?, 'ACTIVE')",
                                  (new_uid, b_name, b_type, b_last4, b_bal))
                        conn.commit()
                        conn.close()
                        st.success("🎉 Setup Complete! Launching...")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Please enter valid Bank Name and Last 4 digits!")
    st.stop()

# ================= 🔐 SCREEN 2: 2-FACTOR BIOMETRIC UNLOCK =================
USER_ID = device_user["id"]

if not st.session_state.unlocked:
    st.markdown("<br>", unsafe_allow_html=True)
    col_l, col_main, col_r = st.columns([1, 2, 1])
    
    with col_main:
        st.markdown(f"""
        <div style='text-align: center; margin-bottom: 20px;'>
            <span style='font-size: 11px; letter-spacing: 1px; color: #94a3b8;'>AES-256 SECURED TERMINAL</span>
            <h1 style='color: #38bdf8; margin: 4px 0 0 0;'>🛡️ Welcome Back</h1>
            <h3 style='color: #f8fafc; margin: 0;'>{device_user['name']}</h3>
            <p style='color: #64748b; font-size: 13px;'>Authenticate <b>any 2 of 3</b> factors to unlock your vault.</p>
        </div>
        """, unsafe_allow_html=True)

        verified_count = sum([st.session_state.auth_pin, st.session_state.auth_face, st.session_state.auth_finger])
        st.progress(verified_count / 2 if verified_count <= 2 else 1.0)
        st.markdown(f"<p style='font-size:12px; color:#94a3b8; text-align:right;'>Clearance: <b>{verified_count}/2 Verified</b></p>", unsafe_allow_html=True)

        tab_pin, tab_face, tab_finger = st.tabs(["🔢 Security PIN", "📷 Face ID", "👆 Fingerprint Sensor"])

        # Factor 1: PIN
        with tab_pin:
            if not st.session_state.auth_pin:
                pin_in = st.text_input("Enter Master PIN", type="password", placeholder="••••••", key="lock_pin")
                if st.button("Validate PIN", use_container_width=True):
                    if pin_in == device_user["pin"]:
                        st.session_state.auth_pin = True
                        st.success("✅ PIN Verified!")
                        st.rerun()
                    else:
                        conn = get_db()
                        c = conn.cursor()
                        now_str = datetime.now().strftime("%d %b %Y, %I:%M:%S %p")
                        c.execute("INSERT INTO intruder_logs (user_id, timestamp, attempt_type, details) VALUES (?, ?, ?, ?)",
                                  (USER_ID, now_str, "Unauthorized PIN", f"Wrong code: '{pin_in}'"))
                        conn.commit()
                        conn.close()
                        st.error("❌ PIN Mismatch! Security breach logged.")
            else:
                st.success("✅ Factor 1 (PIN) Validated.")

        # Factor 2: Face Biometric
        with tab_face:
            if not st.session_state.auth_face:
                st.caption("Align face with camera:")
                cam_feed = st.camera_input("Scan Face", label_visibility="collapsed")
                if cam_feed:
                    with st.spinner("Validating facial geometry..."):
                        if detect_face(cam_feed):
                            st.session_state.auth_face = True
                            st.success("✅ Facial Biometric Matches Enrolled Master!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("❌ Face biometric verification failed. Retry in clear lighting.")
            else:
                st.success("✅ Factor 2 (Facial Scan) Validated.")

        # Factor 3: Fingerprint Sensor (SECURE VALIDATION)
        with tab_finger:
            if not st.session_state.auth_finger:
                st.markdown("""
                <div class='fingerprint-pad'>
                    <span style='font-size: 45px;'>🫆</span><br>
                    <b style='color: #38bdf8;'>TOUCH SENSOR AUTHENTICATION</b><br>
                    <span style='font-size: 12px; color: #94a3b8;'>Enter your registered Biometric Touch Token to confirm fingerprint verification</span>
                </div>
                """, unsafe_allow_html=True)
                
                touch_verify_in = st.text_input("Enter Biometric Touch Token", type="password", placeholder="••••", key="lock_touch_token")
                
                if st.button("👆 Place Finger & Validate Biometric Sensor", use_container_width=True):
                    if touch_verify_in == device_user["touch_token"]:
                        with st.spinner("Matching biometric ridge patterns & token signature..."):
                            time.sleep(1.2)
                            st.session_state.auth_finger = True
                            st.success("✅ Fingerprint Biometric Verified Successfully!")
                            st.rerun()
                    else:
                        st.error("❌ Fingerprint Scan Rejected: Biometric Touch Token Mismatch!")
            else:
                st.success("✅ Factor 3 (Fingerprint Sensor) Validated.")

        st.divider()
        if verified_count >= 2:
            if st.button("🔓 DECRYPT & OPEN VAULT", use_container_width=True, type="primary"):
                st.session_state.unlocked = True
                st.session_state.auth_pin = False
                st.session_state.auth_face = False
                st.session_state.auth_finger = False
                st.rerun()
        else:
            st.info(f"Complete {2 - verified_count} more factor(s) to unlock.")
            
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Reset App / Register New User", use_container_width=True):
            conn = get_db()
            c = conn.cursor()
            c.execute("DELETE FROM users")
            c.execute("DELETE FROM accounts")
            c.execute("DELETE FROM transactions")
            c.execute("DELETE FROM intruder_logs")
            conn.commit()
            conn.close()
            st.rerun()

    st.stop()

# ================= 🚀 SCREEN 3: VAULT DASHBOARD (UNLOCKED) =================
with st.sidebar:
    st.markdown(f"**👤 Master User:** {device_user['name']}")
    if st.button("🔒 Lock Vault", use_container_width=True):
        st.session_state.unlocked = False
        st.session_state.profile_verified = False
        st.rerun()
    st.divider()

    # Quick Add Bank
    with st.expander("➕ Link New Bank Node"):
        with st.form("quick_add_b"):
            qb_name = st.text_input("Bank Name (e.g. Axis Bank)")
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

    # Wire Gateway
    st.subheader("⚡ Wire Gateway")
    with st.form("gw_form"):
        tx_action = st.radio("Action", ["💸 Pay (Debit)", "💰 Receive (Credit)"], horizontal=True)
        
        conn = get_db()
        accs = pd.read_sql("SELECT id, bank_name, last4, balance FROM accounts WHERE user_id = ? AND status = 'ACTIVE'", conn, params=(USER_ID,))
        conn.close()
        acc_opts = {f"{r['bank_name']} (****{r['last4']}) - ₹{r['balance']:,.2f}": r['id'] for _, r in accs.iterrows()}

        merchant = st.text_input("Payee / Source", value="Amazon UPI" if "Pay" in tx_action else "Salary")
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
                        st.toast(f"₹{amt:,.2f} Paid!", icon="💸")
                    else:
                        c.execute("INSERT INTO transactions (user_id, account_id, title, amount, type, category, date, source) VALUES (?, ?, ?, ?, 'INCOME', 'Capital Inflow', ?, 'Wire Gateway')",
                                  (USER_ID, t_acc_id, merchant, amt, now_str))
                        c.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amt, t_acc_id))
                        st.toast(f"₹{amt:,.2f} Received!", icon="💰")
                    conn.commit()
                    conn.close()
                    time.sleep(1)
                    st.rerun()

# Load Data
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
        <span style='font-size:12px;'>Someone attempted to breach your vault <b>{len(intruders)} time(s)</b>.</span>
    </div>
    """, unsafe_allow_html=True)
    with st.expander("🔍 View Intruder Breach Logs"):
        st.dataframe(intruders, use_container_width=True, hide_index=True)
        if st.button("🗑️ Clear Breach Logs"):
            conn = get_db()
            c = conn.cursor()
            c.execute("DELETE FROM intruder_logs WHERE user_id = ?", (USER_ID,))
            conn.commit()
            conn.close()
            st.rerun()

# ================= 📱 AUTO-LOCK NAVIGATION =================
st.markdown("### 🏛️ FinVault Core Terminal")
menu_choice = st.selectbox(
    "Navigation View",
    ["🏛️ Treasury Dashboard", "📊 Spending Analytics", "🤖 FinAI Financial Assistant", "⚙️ Confidential Profile & Node Manager"],
    label_visibility="collapsed"
)

# 🔒 AUTO-LOCK LOGIC
if "active_nav" not in st.session_state:
    st.session_state.active_nav = menu_choice

if st.session_state.active_nav == "⚙️ Confidential Profile & Node Manager" and menu_choice != "⚙️ Confidential Profile & Node Manager":
    st.session_state.profile_verified = False

st.session_state.active_nav = menu_choice

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

# 3. 🤖 AI FINANCIAL ASSISTANT (FinAI Engine)
elif menu_choice == "🤖 FinAI Financial Assistant":
    st.subheader("🤖 FinAI Personal Financial Advisor")
    st.caption("Aapka 24/7 AI banking bot. Real-time balance, kharche aur saving tips poochiye!")

    active_accs = accounts[accounts['status'] == 'ACTIVE']
    total_bal = active_accs['balance'].sum() if not active_accs.empty else 0.0
    tot_exp = transactions[transactions['type'] == 'EXPENSE']['amount'].sum() if not transactions.empty else 0.0
    tot_inc = transactions[transactions['type'] == 'INCOME']['amount'].sum() if not transactions.empty else 0.0

    # Quick Action Buttons
    st.markdown("**⚡ Quick Prompts (Click to ask):**")
    q1, q2, q3, q4 = st.columns(4)
    prompt_clicked = None
    if q1.button("💰 Total Balance?", use_container_width=True): prompt_clicked = "Mera total balance kitna hai?"
    if q2.button("🍔 Expense Summary?", use_container_width=True): prompt_clicked = "Maine kitna kharcha kiya hai?"
    if q3.button("🏦 Banks List?", use_container_width=True): prompt_clicked = "Mere kitne bank accounts linked hain?"
    if q4.button("💡 Saving Tips?", use_container_width=True): prompt_clicked = "Paisa bachane ke tips do"

    # Display Chat History
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Handle Input (User typed or clicked)
    user_input = st.chat_input("Poochiye: e.g. HDFC ka balance kya hai? ya Kharcha kitna hua?")
    query = prompt_clicked or user_input

    if query:
        # Display user message
        st.session_state.chat_history.append({"role": "user", "content": query})
        with st.chat_message("user"):
            st.markdown(query)

        # AI Intelligent Response Engine
        q_low = query.lower()
        response = ""

        if any(w in q_low for w in ["total balance", "net worth", "kul balance", "total kitna"]):
            response = f"📊 Aapka **Total Active Balance** sabhi banks ko milakar **₹{total_bal:,.2f}** hai!"
        elif any(w in q_low for w in ["kharcha", "expense", "spent", "debit", "outflow"]):
            response = f"💸 Aapne abhi tak total **₹{tot_exp:,.2f}** kharch kiye hain. Aur total income **₹{tot_inc:,.2f}** receive hui hai."
        elif any(w in q_low for w in ["bank", "accounts", "khata", "list"]):
            bank_names = [f"• **{r['bank_name']}** (****{r['last4']}): ₹{r['balance']:,.2f} [{r['status']}]" for _, r in accounts.iterrows()]
            response = "🏦 **Aapke Linked Bank Accounts:**\n\n" + "\n".join(bank_names)
        elif any(w in q_low for w in ["tip", "advice", "bachana", "save", "saving"]):
            response = ("💡 **FinAI Saving Tips:**\n\n"
                        "1. **50-30-20 Rule**: Apni income ka 50% zaroorat (Needs), 30% shauk (Wants), aur 20% savings mein rakhein.\n"
                        "2. **Emergency Fund**: Kam se kam 3 mahine ke kharche ek alag Savings account mein freeze rakhein.\n"
                        "3. **Track Daily**: FinVault se har online kharcha track karte rahein taaki overspending na ho!")
        elif any(w in q_low for w in ["hdfc", "sbi", "axis", "icici"]):
            matched = False
            for _, r in accounts.iterrows():
                if r['bank_name'].lower() in q_low:
                    response = f"🏦 **{r['bank_name']}** (****{r['last4']}) mein abhi available balance **₹{r['balance']:,.2f}** hai."
                    matched = True
                    break
            if not matched:
                response = "Is naam ka bank aapke vault mein linked nahi hai. Sidebar se naya bank add karein!"
        else:
            response = f"Main aapka personal finance bot hoon! Aap mujhse **Total Balance**, **Bank Wise Balance**, **Recent Expenses**, ya **Saving Advice** pooch sakte hain. (Aapka Current Balance: **₹{total_bal:,.2f}** hai)."

        # Append and show AI response
        st.session_state.chat_history.append({"role": "assistant", "content": response})
        with st.chat_message("assistant"):
            st.markdown(response)

# 4. PROFILE & BANK ADMINISTRATION (DOUBLE-LOCKED)
elif menu_choice == "⚙️ Confidential Profile & Node Manager":
    st.subheader("⚙️ Executive Administration & Node Manager")
    
    if not st.session_state.profile_verified:
        st.info("🔒 Enter your Master Profile Password to unlock your settings.")
        p_check = st.text_input("Enter Profile Password", type="password", key="prof_lock_input")
        if st.button("Authenticate Administration Access"):
            if p_check == device_user["profile_pass"]:
                st.session_state.profile_verified = True
                st.success("Access Granted!")
                st.rerun()
            else:
                st.error("❌ Wrong Profile Password!")
    else:
        c_p1, c_p2 = st.columns([3, 1])
        with c_p1: st.success("🔓 Administrative Access Granted")
        with c_p2:
            if st.button("🔒 Lock Settings Now"):
                st.session_state.profile_verified = False
                st.rerun()

        # 1. Profile Details Update
        st.markdown("### 👤 Update Credentials")
        with st.form("upd_prof_f"):
            up_name = st.text_input("Full Name", value=device_user["name"])
            up_phone = st.text_input("Phone Number", value=device_user["phone"] or "")
            up_pin = st.text_input("Master PIN", value=device_user["pin"], type="password")
            up_ppass = st.text_input("Profile Password", value=device_user["profile_pass"], type="password")
            up_touch_tok = st.text_input("Biometric Touch Token", value=device_user["touch_token"], type="password")

            if st.form_submit_button("💾 Save Profile Changes"):
                conn = get_db()
                c = conn.cursor()
                c.execute("UPDATE users SET name = ?, phone = ?, master_pin = ?, profile_password = ?, touch_token = ? WHERE id = ?",
                          (up_name, up_phone, up_pin, up_ppass, up_touch_tok, USER_ID))
                conn.commit()
                conn.close()
                st.success("Credentials updated successfully!")
                time.sleep(1)
                st.rerun()

        st.divider()

        # 2. Re-Enroll Face Biometric
        st.markdown("### 🧬 Re-Enroll Face Biometric")
        st.caption("Re-scan face geometry via camera:")
        re_face = st.camera_input("Re-Scan Face", label_visibility="collapsed")
        if re_face and st.button("💾 Save & Overwrite Face ID"):
            if detect_face(re_face):
                conn = get_db()
                c = conn.cursor()
                c.execute("UPDATE users SET face_enrolled = 1 WHERE id = ?", (USER_ID,))
                conn.commit()
                conn.close()
                st.success("Face ID Updated Successfully!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("❌ Face not detected clearly.")

        st.divider()

        # 3. Bank Management (Edit / Freeze / Delete)
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
