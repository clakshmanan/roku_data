

# Roku project via Git Repository with SQLite db

import os
import time
import json
import sqlite3
import pandas as pd
import numpy as np
import streamlit as st
import bcrypt
import plotly.graph_objects as go
import plotly.figure_factory as ff
import plotly.express as px
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from st_aggrid import GridOptionsBuilder, AgGrid, JsCode
from cachetools import TTLCache, cached
import requests
from io import StringIO
from urllib.parse import urljoin
from io import StringIO
from cachetools import cached, TTLCache

# Dark mode toggle button
def dark_mode_toggle():
    if 'dark_mode' not in st.session_state:
        st.session_state.dark_mode = False
    
    # Button in sidebar to toggle dark mode
    if st.sidebar.button('🌙 Dark Mode' if not st.session_state.dark_mode else '☀️ Light Mode'):
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()

# Apply dark mode styles
def apply_dark_mode():
    if st.session_state.get('dark_mode', False):
        st.markdown("""
            <style>
                .stApp {
                    background-color: #0e1117;
                    color: #fafafa;
                }
                .css-18e3th9 {
                    background-color: #0e1117;
                }
                .css-1d391kg {
                    background-color: #0e1117;
                }
                .st-bb {
                    background-color: #0e1117;
                }
                .st-at {
                    background-color: #0e1117;
                }
                .st-ae {
                    background-color: #0e1117;
                }
                .st-af {
                    background-color: #0e1117;
                }
                .stButton>button {
                    color: #fafafa;
                    background-color: #262730;
                    border-color: #fafafa;
                }
                .stTextInput>div>div>input {
                    color: #fafafa;
                    background-color: #262730;
                }
                .stSelectbox>div>div>select {
                    color: #fafafa;
                    background-color: #262730;
                }
                .stNumberInput>div>div>input {
                    color: #fafafa;
                    background-color: #262730;
                }
                .stDateInput>div>div>input {
                    color: #fafafa;
                    background-color: #262730;
                }
                .css-1q8dd3e {
                    color: #fafafa;
                }
                .css-1fv8s86 p {
                    color: #fafafa;
                }
                .css-1fv8s86 h1, .css-1fv8s86 h2, .css-1fv8s86 h3, .css-1fv8s86 h4, .css-1fv8s86 h5, .css-1fv8s86 h6 {
                    color: #fafafa;
                }
                .css-12ttj6m {
                    background-color: #262730;
                }
                .css-1y4p8pa {
                    background-color: #262730;
                }
                .css-1oe5cao {
                    background-color: #262730;
                }
            </style>
        """, unsafe_allow_html=True)

# Page configuration with optimized settings
st.set_page_config(
    page_title="Contec",
    page_icon="🌀",
    layout='wide',
    initial_sidebar_state="expanded"
)

# Remove footer and optimize Streamlit performance
st.markdown("""
    <style>
        footer {visibility: hidden;}
        .stDeployButton {display:none;}
        /* Reduce padding to maximize screen real estate */
        .main .block-container {padding-top: 2rem; padding-bottom: 2rem;}
        /* Optimize column spacing */
        .stHorizontalBlock {gap: 1rem;}
    </style>
""", unsafe_allow_html=True)

# Apply dark mode if enabled
apply_dark_mode()

#----------------------------------------------------------------------------------------------------------------
## database setup with SQLite
class DatabaseManager:
    def __init__(self, db_name='mycontec.db'):
        self.db_name = db_name
        self.init_db()
        
    def init_db(self):
        """Initialize SQLite database with both roku_data and user tables"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Create roku_data table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS roku_data (
            contec_id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            reportdate DATE NOT NULL,
            designator VARCHAR,
            TrackingID VARCHAR,
            invoice_code VARCHAR NOT NULL,
            qty INTEGER NOT NULL,
            rate FLOAT NOT NULL,
            amount FLOAT NOT NULL,
            invoice_number VARCHAR,
            servicecode VARCHAR NOT NULL,
            Palletsize INTEGER,
            PalletCount INTEGER,
            Model VARCHAR NOT NULL,
            TestDate DATE,
            FailureDescription VARCHAR,
            failurecode VARCHAR,
            PartDescription VARCHAR,
            invoicetype VARCHAR NOT NULL,
            Invoice_Reference VARCHAR
        )
        ''')
        
        # Create user credentials table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            is_admin BOOLEAN NOT NULL DEFAULT 0,
            is_superadmin BOOLEAN NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
        ''')
        
        # Create indexes for better performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_reportdate ON roku_data(reportdate)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_servicecode ON roku_data(servicecode)')
        
        # Ensure admin user exists
        admin_password = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cursor.execute('''
        INSERT OR IGNORE INTO users (username, password_hash, is_admin, is_superadmin) 
        VALUES (?, ?, 1, 1)
        ''', ("admin", admin_password))
        
        conn.commit()
        conn.close()
    
    def get_connection(self):
        """Get a database connection"""
        return sqlite3.connect(self.db_name)
    
    def get_roku_data(self):
        """Get all data from roku_data table"""
        conn = self.get_connection()
        try:
            df = pd.read_sql_query("SELECT * FROM roku_data", conn)
            return df
        except Exception as e:
            st.error(f"Error fetching roku_data: {str(e)}")
            return pd.DataFrame()
        finally:
            conn.close()

# Initialize database manager
db_manager = DatabaseManager()

# --------------------------------------------------------------------------------------------------------------------------
class DataLoader:
    def __init__(self):
        self.db_manager = db_manager
    
    @cached(cache=TTLCache(maxsize=2, ttl=1800))
    def load_data(self):
        """Load data from the SQLite database"""
        return self.db_manager.get_roku_data()

# -------------------------------------------------------------------------------------
# Enhanced Authentication class using SQLite
class Authentication:
    def __init__(self):
        self.db_manager = db_manager
    
    def hash_password(self, password):
        """Hash a password for storing."""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def verify_password(self, stored_password, provided_password):
        """Verify a stored password against one provided by user"""
        try:
            return bcrypt.checkpw(provided_password.encode('utf-8'), stored_password.encode('utf-8'))
        except Exception as e:
            st.error(f"Password verification error: {str(e)}")
            return False
    
    def check_credentials(self, username, password):
        """Check if username and password are correct"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            stored_password = user[1]
            if self.verify_password(stored_password, password):
                return {
                    'authenticated': True, 
                    'is_admin': bool(user[2]),
                    'is_superadmin': bool(user[3])
                }
        
        return {'authenticated': False, 'is_admin': False, 'is_superadmin': False}
    
    def create_user(self, username, password, is_admin=False, is_superadmin=False):
        """Create a new user"""
        if not username or not password:
            return False, "Username and password are required"
            
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            # Check if user exists
            cursor.execute('SELECT username FROM users WHERE username = ?', (username,))
            if cursor.fetchone():
                return False, "Username already exists"
            
            # Create new user
            hashed_password = self.hash_password(password)
            cursor.execute('''
                INSERT INTO users (username, password_hash, is_admin, is_superadmin)
                VALUES (?, ?, ?, ?)
            ''', (username, hashed_password, int(is_admin), int(is_superadmin)))
            
            conn.commit()
            return True, "User created successfully"
        except Exception as e:
            conn.rollback()
            return False, f"Error creating user: {str(e)}"
        finally:
            conn.close()
    
    def delete_user(self, username):
        """Delete a user"""
        if username == "admin":
            return False, "Cannot delete admin user"
            
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('DELETE FROM users WHERE username = ?', (username,))
            if cursor.rowcount == 0:
                return False, "User not found"
                
            conn.commit()
            return True, "User deleted successfully"
        except Exception as e:
            conn.rollback()
            return False, f"Error deleting user: {str(e)}"
        finally:
            conn.close()
    
    def update_password(self, username, new_password):
        """Update user password"""
        if not new_password:
            return False, "New password is required"
            
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            hashed_password = self.hash_password(new_password)
            cursor.execute('''
                UPDATE users 
                SET password_hash = ?
                WHERE username = ?
            ''', (hashed_password, username))
            
            if cursor.rowcount == 0:
                return False, "User not found"
                
            conn.commit()
            return True, "Password updated successfully"
        except Exception as e:
            conn.rollback()
            return False, f"Error updating password: {str(e)}"
        finally:
            conn.close()
    
    def list_users(self):
        """List all users"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT username, is_admin, is_superadmin FROM users')
            return cursor.fetchall()
        except Exception as e:
            st.error(f"Error listing users: {str(e)}")
            return []
        finally:
            conn.close()
# ----------------------------------------------------------------------------------------------------------
    def login_page(self):
        """Render the login page with colorful design"""
        col1, col2, col3 = st.columns(3)

        with col1:
            st.image("C:/clak/_alfa_projects/_git_projects/Roku_Contec/contec.png", width=175)
            st.write(" ")
            st.write("An Application product for")
            st.subheader("ROKU_CONTEC")

            #st.image("https://github.com/clakshmanan/Data_Roku/contec.png", width=175)
           
        with col3:
            new_title = '<p style="font-family:sans-serif;text-align:left; color:#1c03fc; font-size: 25px;">🔒 Login </p>'
            st.markdown(new_title, unsafe_allow_html=True)
            
            username = st.text_input("User Name", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            
            if st.button("Login", key="login_button"):
                with st.spinner("Authenticating..."):
                    result = self.check_credentials(username, password)
                    if result['authenticated']:
                        st.session_state['authenticated'] = True
                        st.session_state['username'] = username
                        st.session_state['is_admin'] = result['is_admin']
                        st.session_state['is_superadmin'] = result['is_superadmin']
                        st.toast("Logged in successfully!", icon="✅")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("Invalid credentials!")
                        time.sleep(1)
                        st.rerun()
       
        
# -------------------------------------------------------------------------------------------------------------------------
    def user_management_page(self):
        """User management page for admin/superadmin with colorful design"""
        if not st.session_state.get('is_admin'):
            st.error("Admin privileges required")
            return
        
        st.title("👑 User Management")
        
        # Create new user section with colorful card
        with st.expander("➕ Create New User", expanded=True):
            with st.form("create_user_form"):
                col1, col2 = st.columns(2)
                with col1:
                    new_username = st.text_input("Username", key="new_username")
                with col2:
                    new_password = st.text_input("Password", type="password", key="new_password")
                
                col3, col4 = st.columns(2)
                with col3:
                    is_admin = st.checkbox("Admin User", 
                                         disabled=not st.session_state.get('is_superadmin'),
                                         key="is_admin_checkbox")
                with col4:
                    is_superadmin = st.checkbox("Super Admin", 
                                              disabled=not st.session_state.get('is_superadmin'),
                                              key="is_superadmin_checkbox")
                
                if st.form_submit_button("Create User"):
                    success, message = self.create_user(new_username, new_password, is_admin, is_superadmin)
                    if success:
                        st.success(message)
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(message)
        
        # List all users with delete option in colorful cards
        st.subheader("👥 Current Users")
        users = self.list_users()
        if users:
            for username, is_admin, is_superadmin in users:
                # Determine card color based on user role
                if is_superadmin:
                    card_color = "linear-gradient(135deg, #ff9a9e 0%, #fad0c4 100%)"
                elif is_admin:
                    card_color = "linear-gradient(135deg, #a1c4fd 0%, #c2e9fb 100%)"
                else:
                    card_color = "linear-gradient(135deg, #d4fc79 0%, #96e6a1 100%)"
                
                with st.expander(f"{username} {'👑' if is_superadmin else '🔑' if is_admin else '👤'}"):
                    st.markdown(
                        f"""
                        <div style="
                            background: {card_color};
                            padding: 1rem;
                            border-radius: 10px;
                            margin-bottom: 1rem;
                        ">
                            <h4>{username}</h4>
                            <p>Role: {'Super Admin' if is_superadmin else 'Admin' if is_admin else 'Regular User'}</p>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    
                    with st.form(f"edit_user_{username}"):
                        new_password = st.text_input("New Password", type="password", key=f"pw_{username}")
                        if st.form_submit_button("Update Password") and new_password:
                            success, message = self.update_password(username, new_password)
                            if success:
                                st.success(message)
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(message)

                    # Only allow deletion if current user is superadmin and not deleting themselves
                    if st.session_state.get('is_superadmin') and username != st.session_state.get('username'):
                        with st.form(key=f"delete_form_{username}"):
                            submit = st.form_submit_button(label=f"❌ Delete User {username}")
                            if submit:
                                success, message = self.delete_user(username)
                                if success:
                                    st.success(message)
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error(message)
        else:
            st.warning("No users found")

# -------------------------------------------------------------------------------------
# Your existing ContecApp class with all original methods (alfa, beta, charlie, delta, echo)
# Modified to use DataLoader instead of SQLiteLoader
class ContecApp:
    def __init__(self):
        self.data_loader = DataLoader()
        
    @cached(cache=TTLCache(maxsize=2, ttl=1800))
    def fetch_data(self):
        """Fetch data from SQLite database with caching"""
        return self.data_loader.load_data()
    
    def home_page(self):
        st.markdown(
            '<p style="font-family:sans-serif;text-align:center; color:#42b6f5; font-size: 25px;">✨ CONTEC CHENNAI LOCATION ✨</p>',
            unsafe_allow_html=True
        )
        st.divider()
        st.subheader("Analysis on Roku Data")
        pan1, pan2 = st.columns(2)
        with pan1:
            st.write("")
            st.write("")
            st.write("✔️...Roku Monthly Revenue Histogram as week wise")
            st.write("✔️...Roku Weekly comparision with Quantity and Amount")
            st.write("✔️...Roku Servicecode wise weekly Data view")
            st.write("✔️...A Statistical view of Roku 2025 Data ")
            st.write("✔️...An Analysis on Roku 2025 Dataset")
            
        with pan2:
            def simulation_graph(data):
                fig = go.Figure(data=[go.Scatter(x=data['time'], y=data['value'])])
                fig.update_layout(
                    xaxis_title="Time",
                    yaxis_title="Value",
                    width=400,
                    height=300
                )
                return fig

            def graph():
                time_steps = np.arange(0, 20, 0.1)
                values = [np.random.normal(loc=5, scale=1.5) for _ in time_steps]
                simulation_data = {'time': time_steps, 'value': values}
                st.plotly_chart(simulation_graph(simulation_data), use_container_width=False)
            
            graph()
    
    @cached(cache=TTLCache(maxsize=2, ttl=1800))
    def alfa(self):
        st.markdown(
            '<p style="font-family:sans-serif;text-align:center; color:#83e6e6; font-size: 25px;">MONTH-WISE-REVENUE-GRAPH</p>',
            unsafe_allow_html=True
        )
        
        col1, col2, col3 = st.columns(3)
        with col1:
            year = st.number_input("📅 Year", min_value=2000, max_value=2100, value=datetime.now().year)
        with col2:
            month = st.selectbox("Month", list(range(1, 13)), format_func=lambda x: datetime(2000, x, 1).strftime('%B'))
        with col3:
            invoice_code = st.text_input("🔑 Invoice Code", value="ROKU")

        @cached(cache=TTLCache(maxsize=2, ttl=1800))
        def fetch_weekly_data(year, month):
            df = self.fetch_data()
            if df.empty:
                return pd.DataFrame()
            
            # Convert columns to proper types
            df['reportdate'] = pd.to_datetime(df['reportdate'])
            df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
            
            # Filter data for the selected year and month
            filtered = df[(df['reportdate'].dt.year == year) & 
                        (df['reportdate'].dt.month == month)]
            
            if filtered.empty:
                return pd.DataFrame()
            
            # Group by week
            weekly_data = filtered.groupby(filtered['reportdate'].dt.isocalendar().week).agg({
                'reportdate': ['min', 'max'],
                'amount': 'sum'
            }).reset_index()
            
            weekly_data.columns = ['week_number', 'start_date', 'end_date', 'total_amount']
            weekly_data['total_amount'] = weekly_data['total_amount'].round(2)
            
            return weekly_data

        with st.spinner("Loading data..."):
            weekly_data = fetch_weekly_data(year, month)
        
        if not weekly_data.empty:
            st.markdown(
                f"<h4 style='text-align: center; font-family: Arial, sans-serif; font-weight: bold; color:#4242cf;'>📅 {datetime(2000, month, 1).strftime('%B')} {year} - Metrics</h4>",
                unsafe_allow_html=True
            )
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=weekly_data['week_number'],
                y=weekly_data['total_amount'],
                mode='lines+markers',
                name='Current Week',
                line=dict(color='blue', width=3),
                marker=dict(size=6, color='blue', symbol='circle')
            ))
            
            previous_week_amounts = [0] + weekly_data['total_amount'].tolist()[:-1]
            fig.add_trace(go.Scatter(
                x=weekly_data['week_number'],
                y=previous_week_amounts,
                mode='lines+markers',
                name='Previous Week',
                line=dict(color='red', width=3, dash='dash'),
                marker=dict(size=6, color='red', symbol='circle')
            ))
            
            fig.update_layout(
                title='📊 Current vs Previous Week Comparison',
                xaxis_title='Week Number',
                yaxis_title='Total Amount',
                template='plotly_white',
                font=dict(family='Arial, sans-serif', size=12, color='#2C3E50'),
                legend=dict(x=0.02, y=0.98, borderwidth=1),
                height=450
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("⚠️ No data found for the selected filters.")

    def beta(self):
        st.markdown(
            "<h3 style='text-align: center; font-family: Arial, sans-serif; font-weight: bold; color:#0cb3f0;'>📊Roku Week-Wise Data</h3>",
            unsafe_allow_html=True
        )

        @cached(cache=TTLCache(maxsize=2, ttl=1800))
        def fetch_weekly_data(year, month):
            df = self.fetch_data()
            if df.empty:
                return pd.DataFrame()
            
            # Convert columns to proper types
            df['reportdate'] = pd.to_datetime(df['reportdate'])
            df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
            df['qty'] = pd.to_numeric(df['qty'], errors='coerce')
            
            # Filter data for the selected year and month
            filtered = df[(df['reportdate'].dt.year == year) & 
                        (df['reportdate'].dt.month == month)]
            
            if filtered.empty:
                return pd.DataFrame()
            
            # Group by week
            weekly_data = filtered.groupby(filtered['reportdate'].dt.isocalendar().week).agg({
                'reportdate': ['min', 'max'],
                'amount': 'sum',
                'qty': 'sum'
            }).reset_index()
            
            weekly_data.columns = ['week_number', 'start_date', 'end_date', 'total_amount', 'total_quantity']
            weekly_data['total_amount'] = weekly_data['total_amount'].round(2)
            weekly_data['total_quantity'] = weekly_data['total_quantity'].astype(int)
            
            return weekly_data

        col1, col2, col3 = st.columns(3)
        with col1:
            year = st.number_input("📅 Year", min_value=2000, max_value=2100, value=datetime.now().year)
        with col2:
            month = st.selectbox(".Month", list(range(1, 13)), format_func=lambda x: datetime(2000, x, 1).strftime('%B'))
        with col3:
            invoice_code = st.text_input("🔑 Invoice Code", value="ROKU")
        st.divider()
        
        with st.spinner("Loading data..."):
            weekly_data = fetch_weekly_data(year, month)
        
        if not weekly_data.empty:
            st.markdown(
                f"<h4 style='text-align: center; font-family: Arial, sans-serif; font-weight: bold; color: #0cb3f0;'>📅 {datetime(2000, month, 1).strftime('%B')} {year} - Weekly Metrics</h4>",
                unsafe_allow_html=True
            )
            
            card_style = """
                <style>
                    .metric-card {
                        background-color:#7ad7ff;
                        border-radius: 14px;
                        padding: 24px;
                        margin: 14px;
                        box-shadow: 0px 4px 8px rgba(0, 0, 0, 0.2);
                        text-align: left;
                        font-family: Arial, sans-serif;
                    }
                    .metric-header {
                        font-size: 14px;
                        font-weight: bold;
                        color: #333;
                    }
                    .metric-value {
                        font-size: 14px;
                        font-weight: bold;
                        color: #c9497a;
                    }
                </style>
            """
            st.markdown(card_style, unsafe_allow_html=True)
            
            for index, row in weekly_data.iterrows():
                week_number = str(row["week_number"])  # Convert to string
                start_date = row["start_date"]
                end_date = row["end_date"]
                total_qty = f"{int(row['total_quantity']):,}"  # Convert to int and format
                total_amount = f"${float(row['total_amount']):,.2f}"  # Convert to float and format
                prev_amount = float(weekly_data.iloc[index - 1]['total_amount']) if index > 0 else float(row['total_amount'])
                
                col1, col2, col3 = st.columns([1, 1, 2])
                with col1:
                    st.markdown(f"""
                        <div class="metric-card">
                            <div class="metric-header"> Week {week_number}📦</div>
                            <div class="metric-value">Units: {total_qty}</div>
                        </div>
                    """, unsafe_allow_html=True)
                with col2:
                    st.markdown(f"""
                        <div class="metric-card">
                            <div class="metric-header"> Week {week_number}💰</div>
                            <div class="metric-value">Amount: {total_amount}</div>
                        </div>
                    """, unsafe_allow_html=True)
                st.markdown("<hr>", unsafe_allow_html=True)
                with col3:
                    wave_fig = go.Figure()
                    wave_fig.add_trace(go.Scatter(
                        x=[start_date, end_date],
                        y=[prev_amount, float(row['total_amount'])],  # Ensure float conversion
                        mode="lines+markers",
                        name=f"Comparison - Week {week_number}",
                        line=dict(shape="spline", color="#1f77b4", width=3),
                        marker=dict(size=4, symbol="circle", color="#1f77b4"),
                    ))
                    wave_fig.update_layout(
                        title=f'compared with week {int(week_number) - 1}📊 ',  # Convert to int for arithmetic
                        xaxis_title='Date',
                        yaxis_title='Amount',
                        template="plotly_white",
                        height=250,
                        font=dict(family="Arial, sans-serif", size=12, color="#2C3E50")
                    )
                    st.plotly_chart(wave_fig, use_container_width=True)
                st.markdown("<hr>", unsafe_allow_html=True)
                time.sleep(1)
        else:
            st.warning("⚠️ No data found for the selected filters.")

    @cached(cache=TTLCache(maxsize=2, ttl=1800))
    def charlie(self):
        @cached(cache=TTLCache(maxsize=2, ttl=1800))
        def fetch_data(from_date, to_date):
            df = self.fetch_data()
            if df.empty:
                return pd.DataFrame()
            
            # Convert columns to proper types
            df['reportdate'] = pd.to_datetime(df['reportdate'])
            df['qty'] = pd.to_numeric(df['qty'], errors='coerce')
            df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
            
            filtered = df[(df['reportdate'] >= pd.to_datetime(from_date)) & 
                        (df['reportdate'] <= pd.to_datetime(to_date))]
            
            return filtered

        new_title = '<p style="font-family:sans-serif;text-align:center; color:#5142f5; font-size: 25px;">🌍 ROKU SERVICECODE DATA 🌍</p>'
        st.markdown(new_title, unsafe_allow_html=True)
        st.markdown("#### Select your week between")
        
        col1, col2 = st.columns(2)
        with col1:
            from_date = st.date_input("From Date", value=datetime(2025, 1, 1))
        with col2:
            to_date = st.date_input("To Date", value=datetime.today())

        with st.spinner("Loading data..."):
            df = fetch_data(from_date, to_date)
        
        if "selected_service" not in st.session_state:
            st.session_state.selected_service = None
        
        if not df.empty:
            def calculate_metrics(df):
                df = df.copy()
                df['WeekStart'] = df['reportdate'] - pd.to_timedelta(df['reportdate'].dt.weekday + 1, unit='d')
                weekly_metrics = df.groupby(['servicecode', 'WeekStart']).agg({
                    'qty': 'sum',
                    'amount': 'sum'
                }).reset_index()
                weekly_metrics['qty'] = weekly_metrics['qty'].astype(int)  # Convert to int
                weekly_metrics['amount'] = weekly_metrics['amount'].round(2)  # Round to 2 decimals
                return weekly_metrics
            
            weekly_metrics = calculate_metrics(df)
            
            if st.session_state.selected_service is None:
                st.markdown("##### Metrics of the week")
                cols = st.columns(3)
                for idx, row in weekly_metrics.iterrows():
                    with cols[idx % 3]:
                        card = st.container()
                        card.markdown(
                        f"""
                        <div style='border:2px solid #4CAF50; box-shadow: 2px 2px 10px rgba(0, 0, 0, 0.1); padding:10px; border-radius:10px; text-align:center;'>
                            <h4 style='color:#20b6c7;'>{row['servicecode']}</h4>
                            <p style='color:#60eb8a ;'>Qty: {int(row['qty'])}</p>
                            <p style='color:#eef7da;'>Amount: ${float(row['amount']):,.2f}</p>
                            <button onclick="window.location.href='?selected_service={row['servicecode']}'">👇</button>
                        </div>
                        """,
                        unsafe_allow_html=True
                        )

                        if st.button(f"View {row['servicecode']} Data", key=idx):
                            st.session_state.selected_service = row['servicecode']
                            st.rerun()
            else:
                selected_service = st.session_state.selected_service
                selected_data = df[df['servicecode'] == selected_service]
                st.subheader(f"{selected_service} Data")
                AgGrid(selected_data)
                if st.button("Back"):
                    st.session_state.selected_service = None
                    st.rerun()
        else:
            st.warning("No data found for the selected date range.")

    @cached(cache=TTLCache(maxsize=2, ttl=1800))
    def delta(self):
        @cached(cache=TTLCache(maxsize=2, ttl=1800))
        def fetch_statistical_data():
            df = self.fetch_data()
            if df.empty:
                return pd.DataFrame()
            
            # Convert columns to proper types
            df['reportdate'] = pd.to_datetime(df['reportdate'])
            df['qty'] = pd.to_numeric(df['qty'], errors='coerce')
            df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
            
            return df

        with st.spinner("Loading data..."): 
            df = fetch_statistical_data()
        
        st.markdown(
            '<p style="font-family:sans-serif;text-align:center; color:#2803fc; font-size: 25px;">📊✨ ROKU DATA SET ✨📊</p>',
            unsafe_allow_html=True
        )
        st.header("Roku Statistics")
        st.divider()
        
        if not df.empty:
            df['reportdate'] = pd.to_datetime(df['reportdate'])
            df['Week'] = df['reportdate'].dt.isocalendar().week.astype(str)  # Convert to string
            df['Month'] = df['reportdate'].dt.month.astype(str)  # Convert to string
            df['Quarter'] = df['reportdate'].dt.quarter.astype(str)  # Convert to string
            df['HalfYear'] = ((df['reportdate'].dt.month - 1) // 6 + 1).astype(str)  # Convert to string
            
            col1,col2 = st.columns(2)
            with col1:
                time_period = st.selectbox("Select Time Period", ["Weekly", "Monthly", "Quarterly", "Half-Yearly"])
                
                if time_period == "Weekly":
                    grouped_data = df.groupby(['Week', 'servicecode']).agg({
                        'qty': 'sum',
                        'amount': 'sum'
                    }).reset_index()
                elif time_period == "Monthly":
                    grouped_data = df.groupby(['Month', 'servicecode']).agg({
                        'qty': 'sum',
                        'amount': 'sum'
                    }).reset_index()
                elif time_period == "Quarterly":
                    grouped_data = df.groupby(['Quarter', 'servicecode']).agg({
                        'qty': 'sum',
                        'amount': 'sum'
                    }).reset_index()
                elif time_period == "Half-Yearly":
                    grouped_data = df.groupby(['HalfYear', 'servicecode']).agg({
                        'qty': 'sum',
                        'amount': 'sum'
                    }).reset_index()
                
                # Convert numeric columns to proper types
                grouped_data['qty'] = grouped_data['qty'].astype(int)
                grouped_data['amount'] = grouped_data['amount'].round(2)
                
                grid_options = GridOptionsBuilder.from_dataframe(grouped_data)
                grid_options.configure_default_column(
                    enablePivot=True, enableValue=True, enableRowGroup=True, sortable=True, filterable=True)
                grid_options.configure_pagination(paginationAutoPageSize=True)
                AgGrid(grouped_data, gridOptions=grid_options.build())
            with col2:
                Graph = st.selectbox("Select Histogram",["Pie_Chart", "Line_Chart", "Bar_Chart", "Scatter_Chart"])
                if Graph == "Pie_Chart":
                    st.plotly_chart(px.pie(grouped_data, values='amount', names='servicecode', title='Proportion of Amount by Servicecode-2025'), use_container_width=True)
                elif Graph == 'Line_Chart':
                    st.plotly_chart(px.line(grouped_data, x=grouped_data.columns[0], y='amount', color='servicecode', markers=True), use_container_width=True)
                elif Graph == 'Bar_Chart':
                    st.plotly_chart(px.bar(grouped_data, y=grouped_data.columns[0], x='amount', color='servicecode', barmode='group', orientation='h'), use_container_width=True)
                elif Graph == 'Scatter_Chart':
                    st.plotly_chart(px.scatter(grouped_data, x=grouped_data.columns[0], y='amount', color='servicecode'), use_container_width=True)

            st.divider()
            st.markdown("### ROKU DATA SET")
            grid_options = GridOptionsBuilder.from_dataframe(df)
            grid_options.configure_default_column(
                enablePivot=True, enableValue=True, enableRowGroup=True, sortable=True, filterable=True)
            grid_options.configure_pagination(paginationAutoPageSize=True)
            AgGrid(df, gridOptions=grid_options.build())
            st.divider()
#---------------------------------------------------------------------------------------------------------------------------
    @cached(cache=TTLCache(maxsize=2, ttl=1800))
    def echo(self):
        st.markdown(
            '<p style="font-family:sans-serif;text-align:center; color:#3bc0f5; font-size: 30px;">📊ANALYSIS ON ROKU DATA📊</p>',
            unsafe_allow_html=True
        )
        st.divider()
        
        @cached(cache=TTLCache(maxsize=2, ttl=1800))
        def fetch_roku_data():
            return self.fetch_data()

        # Fetch data
        with st.spinner("Loading data..."):
            df = fetch_roku_data()
            
        if df is not None and not df.empty:
            try:
                # Convert columns to appropriate types
                df['reportdate'] = pd.to_datetime(df['reportdate'], errors='coerce')
                df['qty'] = pd.to_numeric(df['qty'], errors='coerce')
                df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
                df['rate'] = pd.to_numeric(df['rate'], errors='coerce')

                # Drop rows with missing important values
                df.dropna(subset=['reportdate', 'qty', 'amount', 'rate'], inplace=True)

                # Add date parts
                df['Week'] = df['reportdate'].dt.isocalendar().week
                df['Month'] = df['reportdate'].dt.month
                df['Quarter'] = df['reportdate'].dt.quarter
                df['Year'] = df['reportdate'].dt.year

            except Exception as e:
                st.error(f"Error processing data: {e}")
            else:
                required_cols = ['reportdate', 'servicecode', 'Model', 'rate', 'qty', 'amount']
# copying from old files
                if not all(col in df.columns for col in required_cols):
                    st.error(f"❌ Data file must contain these columns: {', '.join(required_cols)}")
                    st.divider()
                else:
                    # Display data summary
                    st.subheader("📌Data Summary")
                    col_summary1, col_summary2,col_summary3 = st.columns(3)
                    with col_summary1:
                        st.metric("Total Records", len(df))
                    with col_summary3:
                        st.metric("Total Revenue", f"${df['amount'].sum():,.2f}")
                    with col_summary2:
                        st.metric("Total Quantity", f"{df['qty'].sum():,}")
                    st.divider()
                        
                    # Tabs layout
                    tab1, tab2, tab3 = st.tabs(["📌 Summary", "📈 Trend Analysis", "📅 Time-based Insights"])
                    st.divider()

                    with tab1:
                        st.subheader("📌 High & Low Revenue Models")
                            
                        # Calculate metrics
                        total_revenue = df['amount'].sum()
                        total_qty = df['qty'].sum()
                        avg_rate = df['rate'].mean()
                            
                        # Create metric columns
                        col_metrics1, col_metrics2, col_metrics3 = st.columns(3)
                        with col_metrics3:
                            st.metric("Total Revenue", f"${total_revenue:,.2f}")
                        with col_metrics2:
                            st.metric("Total Quantity", f"{total_qty:,}")
                        with col_metrics1:
                            st.metric("Average Rate", f"${avg_rate:,.2f}")
                            st.divider()

                        col1, col2 = st.columns(2)

                        with col1:
                            # Highest 3 Models by Quantity
                            top_qty = df.groupby("Model")["qty"].sum().sort_values(ascending=False).head(3)
                            st.write("### 🔼 Highest 3 Models by Quantity")
                            
                            # Configure AgGrid
                            gb_qty = GridOptionsBuilder.from_dataframe(
                                top_qty.reset_index().rename(columns={'qty': 'Total Quantity'})
                            )
                            gb_qty.configure_column("Model", headerName="Model", width=150)
                            gb_qty.configure_column("Total Quantity", 
                                                headerName="Total Quantity", 
                                                type=["numericColumn", "numberColumnFilter"],
                                                width=120)
                            gb_qty.configure_default_column(
                                resizable=True,
                                filterable=True,
                                sortable=True,
                                editable=False
                            )
                            grid_options_qty = gb_qty.build()
                            
                            AgGrid(
                                top_qty.reset_index().rename(columns={'qty': 'Total Quantity'}),
                                gridOptions=grid_options_qty,
                                height=120,
                                theme='streamlit',
                                fit_columns_on_grid_load=True
                            )
                            
                            # Highest 3 Models by Revenue
                            top_amount = df.groupby("Model")["amount"].sum().sort_values(ascending=False).head(3)
                            st.write("### 🔼 Highest 3 Models by Revenue")
                            
                            # Configure AgGrid
                            gb_amount = GridOptionsBuilder.from_dataframe(
                                top_amount.reset_index().rename(columns={'amount': 'Total Revenue ($)'})
                            )
                            gb_amount.configure_column("Model", headerName="Model", width=150)
                            gb_amount.configure_column("Total Revenue ($)",
                                                    headerName="Total Revenue ($)",
                                                    type=["numericColumn", "numberColumnFilter"],
                                                    width=150,
                                                    valueFormatter="value.toLocaleString('en-US', {style: 'currency', currency: 'USD', minimumFractionDigits: 2})")
                            gb_amount.configure_default_column(
                                resizable=True,
                                filterable=True,
                                sortable=True,
                                editable=False
                            )
                            grid_options_amount = gb_amount.build()
                            
                            AgGrid(
                                top_amount.reset_index().rename(columns={'amount': 'Total Revenue ($)'}),
                                gridOptions=grid_options_amount,
                                height=120,
                                theme='streamlit',
                                fit_columns_on_grid_load=True
                            )
                        
                                                         
                        with col2:
                            # Least 3 Models by Quantity
                            bottom_qty = df.groupby("Model")["qty"].sum().sort_values(ascending=True).head(3)
                            st.write("### 🔽 Least 3 Models by Quantity")
                            
                            # Configure AgGrid
                            gb_bottom_qty = GridOptionsBuilder.from_dataframe(
                                bottom_qty.reset_index().rename(columns={'qty': 'Total Quantity'})
                            )
                            gb_bottom_qty.configure_column("Model", headerName="Model", width=150)
                            gb_bottom_qty.configure_column("Total Quantity", 
                                                        headerName="Total Quantity", 
                                                        type=["numericColumn", "numberColumnFilter"],
                                                        width=120)
                            gb_bottom_qty.configure_default_column(
                                resizable=True,
                                filterable=True,
                                sortable=True,
                                editable=False
                            )
                            grid_options_bottom_qty = gb_bottom_qty.build()
                            
                            AgGrid(
                                bottom_qty.reset_index().rename(columns={'qty': 'Total Quantity'}),
                                gridOptions=grid_options_bottom_qty,
                                height=120,
                                theme='streamlit',
                                fit_columns_on_grid_load=True
                            )
                            
                            # Least 3 Models by Revenue
                            bottom_amount = df.groupby("Model")["amount"].sum().sort_values(ascending=True).head(3)
                            st.write("### 🔽 Least 3 Models by Revenue")
                            
                            # Configure AgGrid
                            gb_bottom_amount = GridOptionsBuilder.from_dataframe(
                                bottom_amount.reset_index().rename(columns={'amount': 'Total Revenue ($)'})
                            )
                            gb_bottom_amount.configure_column("Model", headerName="Model", width=150)
                            gb_bottom_amount.configure_column("Total Revenue ($)",
                                                            headerName="Total Revenue ($)",
                                                            type=["numericColumn", "numberColumnFilter"],
                                                            width=150,
                                                            valueFormatter="value.toLocaleString('en-US', {style: 'currency', currency: 'USD', minimumFractionDigits: 2})")
                            gb_bottom_amount.configure_default_column(
                                resizable=True,
                                filterable=True,
                                sortable=True,
                                editable=False
                            )
                            grid_options_bottom_amount = gb_bottom_amount.build()
                            
                            AgGrid(
                                bottom_amount.reset_index().rename(columns={'amount': 'Total Revenue ($)'}),
                                gridOptions=grid_options_bottom_amount,
                                height=120,
                                theme='streamlit',
                                fit_columns_on_grid_load=True
                            )

                    with tab2:
                        st.subheader("📈 Revenue & Quantity Trends")
                        st.divider()
                            
                        # Calculate daily trends
                        revenue_trend = df.groupby("reportdate")["amount"].sum()
                        qty_trend = df.groupby("reportdate")["qty"].sum()
                            
                        # Create metric columns for trends
                        col_trend1, col_trend2 = st.columns(2)

                        with col_trend1:
                            st.metric("Peak Revenue Per Day", 
                                    f"${revenue_trend.max():,.2f}", 
                                    revenue_trend.idxmax().strftime('%Y-%m-%d'))
                        with col_trend2:
                            st.metric("Peak Quantity Per Day", 
                                    f"{qty_trend.max():,}", 
                                    qty_trend.idxmax().strftime('%Y-%m-%d'))
                        st.divider()

                        # Service code analysis
                        col_service1, col_service2 = st.columns(2)
                        with col_service1:
                            st.write("### �️ Most Frequent ServiceCode")
                            freq_service = df['servicecode'].value_counts().head(10)
                            st.dataframe(freq_service.reset_index().rename(
                                columns={'index': 'ServiceCode', 'servicecode': 'Count'}))

                        with col_service2:
                            st.write("### 💰 Highest Revenue-Generating ServiceCode")
                            revenue_service = df.groupby("servicecode")["amount"].sum().sort_values(ascending=False).head(10)
                            st.dataframe(revenue_service.reset_index().rename(
                                columns={'amount': 'Total Revenue ($)'}))

                         # Average rate analysis
                        avg_rate = df.groupby("Model")["rate"].mean().sort_values(ascending=False)
                        st.write("### 🧮 Average Rate per Model")
                        st.dataframe(avg_rate.reset_index().rename(columns={'rate': 'Average Rate ($)'}))
                        st.divider()

                        st.subheader("Plot Trend")
                        # Plot trends
                        fig, ax = plt.subplots(figsize=(12, 5))
                        revenue_trend.plot(ax=ax, label="Revenue", color='green')
                        qty_trend.plot(ax=ax, label="Quantity", color='blue')
                        ax.legend()
                        ax.set_title("📆 Daily Revenue & Quantity Trend")
                        ax.set_ylabel("Amount / Quantity")
                        st.pyplot(fig)

                    with tab3:
                        st.subheader("📅 Model Analysis")
                        st.divider()
                        
                        # Time-based model occurrence
                        # Weekly counts
                        # Group data
                        weekly_model = df.groupby(["Year", "Week", "Model"]).size().reset_index(name='count')
                        # Sort and filter top 10
                        top10_weekly_model = weekly_model.sort_values(by="count", ascending=False).head(10)
                        # Display with AgGrid
                        st.write("### 📆 Weekly Occurrences (Top 10)")
                        # Set AgGrid options
                        gb = GridOptionsBuilder.from_dataframe(top10_weekly_model)
                        gb.configure_default_column(cellStyle={'textAlign': 'center'})
                        gb.configure_grid_options(domLayout='autoHeight')
                        gridOptions = gb.build()
                        AgGrid(top10_weekly_model, gridOptions=gridOptions, height=400, fit_columns_on_grid_load=True)
                    
                        # Group by Year, Month, and Model
                        monthly_model = df.groupby(["Year", "Month", "Model"]).size().reset_index(name='count')
                        # Sort and filter top 10
                        top10_monthly_model = monthly_model.sort_values(by='count', ascending=False).head(10)
                        # Display header
                        st.write("### 📆 Monthly Occurrences (Top 10)")
                        # Build grid options
                        gb = GridOptionsBuilder.from_dataframe(top10_monthly_model)
                        # Center align both cells and headers
                        gb.configure_default_column(
                            cellStyle={'textAlign': 'center'},
                            headerStyle={'textAlign': 'left'}
                        )
                        # Other grid settings
                        gb.configure_grid_options(domLayout='autoHeight')
                        gridOptions = gb.build()

                        # Display the AgGrid
                        AgGrid(top10_monthly_model, gridOptions=gridOptions, height=400, fit_columns_on_grid_load=True)
                        #---------------------------------------------------------------------
                        quarterly_model = df.groupby(["Year", "Quarter", "Model"]).size().reset_index(name='count')
                        st.write("### 📆 Quarterly Occurrences (Top 10)")

                        gb = GridOptionsBuilder.from_dataframe( quarterly_model)
                        gb.configure_default_column(cellStyle={'textAlign': 'center'})
                        gb.configure_grid_options(domLayout='normal')
                        gridOptions = gb.build()
                        AgGrid( quarterly_model, gridOptions=gridOptions, height=400, fit_columns_on_grid_load=True)
                        
                        # Revenue share pie chart
                        st.write("### 📊 Revenue Share by Top 10 Models")
                        revenue_share = df.groupby("Model")["amount"].sum().sort_values(ascending=False).head(10)
                        
                        col_pie1, col_pie2 = st.columns([1, 2])
                        
                        with col_pie1:
                            st.dataframe(
                            revenue_share.reset_index()
                            .rename(columns={'amount': 'Total Revenue ($)'})
                            .style
                            .format({'Total Revenue ($)': '{:,.2f}'})  # Format to 2 decimal places
                            .set_properties(**{'text-align': 'center'}),
                            use_container_width=True
                        )

                        with col_pie2:
                            fig2, ax2 = plt.subplots()
                            ax2.pie(revenue_share, labels=revenue_share.index, autopct='%1.1f%%', startangle=140)
                            ax2.axis('equal')
                            st.pyplot(fig2)

class AppExe:
    def __init__(self):
        try:
            self.auth = Authentication()
            self.app = ContecApp()
        except Exception as e:
            st.error(f"Application initialization failed: {str(e)}")
            st.stop()  # Prevent further execution
        
    @cached(cache=TTLCache(maxsize=2, ttl=1800))
    def run(self):
        if 'authenticated' not in st.session_state:
            st.session_state['authenticated'] = False
        
        if not st.session_state['authenticated']:
            self.auth.login_page()
        else:
            with st.sidebar:
                dark_mode_toggle()  # Add dark mode toggle to sidebar
                st.image("contec.png", width=175)
                
                # Add user management option for admins
                if st.session_state.get('is_admin') or st.session_state.get('is_superadmin'):
                    if st.sidebar.button("👑 User Management"):
                        st.session_state['current_page'] = 'user_management'
                
                st.sidebar.header("Roku_Data")
                options = st.sidebar.selectbox(
                    "Select_Service:",
                    ["Home_Page","1️⃣Monthly_Revenue_Graph", "2️⃣Weekly_Revenue_Data", "3️⃣Weekly_Services_Data", 
                     "4️⃣Statistical_Data","5️⃣Analysis_Data"])
                
                if st.sidebar.button("Logout"):
                    st.session_state.update({
                        'authenticated': False,
                        'username': None,
                        'is_admin': False,
                        'is_superadmin': False,
                        'current_page': None
                    })
                    st.rerun()
            
            # Check if we're on the user management page
            if st.session_state.get('current_page') == 'user_management':
                self.auth.user_management_page()
            else:
                # Your existing page routing
                if options == "Home_Page":
                    self.app.home_page()
                elif options == "1️⃣Monthly_Revenue_Graph":
                    self.app.alfa()
                elif options == "2️⃣Weekly_Revenue_Data":
                    self.app.beta()
                elif options == "3️⃣Weekly_Services_Data":
                    self.app.charlie()
                elif options == "4️⃣Statistical_Data":
                    self.app.delta()
                elif options == "5️⃣Analysis_Data":
                    self.app.echo()

if __name__ == "__main__":
    try:
        AppExe().run()
    except Exception as e:
        st.error(f"Application error: {str(e)}")
        st.stop()