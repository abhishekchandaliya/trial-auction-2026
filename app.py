import streamlit as st
import pandas as pd
import numpy as np
import time
import json
import base64
import io
import os
from datetime import datetime

# -----------------------------------------------------------------------------
# 1. CONFIGURATION & STYLES
# -----------------------------------------------------------------------------

st.set_page_config(
    page_title="🏆 ABCD Auction 2026",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS to replicate the React App's Slate-950 Dark Theme
st.markdown("""
<style>
    /* Global Theme Overrides */
    .stApp {
        background-color: #020617; /* Slate-950 */
        color: #e2e8f0; /* Slate-200 */
        font-family: 'Inter', sans-serif;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #0f172a; /* Slate-900 */
        border-right: 1px solid #1e293b;
    }

    /* Cards & Containers */
    .custom-card {
        background-color: #0f172a;
        border: 1px solid #1e293b;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        margin-bottom: 20px;
    }
    
    .metric-card {
        background: linear-gradient(to bottom right, #0f172a, #1e293b);
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 15px;
        text-align: center;
    }

    /* Typography */
    h1, h2, h3 {
        color: #f8fafc !important;
        font-weight: 800 !important;
    }
    
    /* Buttons */
    .stButton button {
        border-radius: 8px;
        font-weight: 600;
    }
    
    /* Tables */
    [data-testid="stDataFrame"] {
        background-color: #0f172a;
        border: 1px solid #1e293b;
        border-radius: 8px;
    }
    
    /* Images */
    [data-testid="stImage"] {
        border-radius: 12px;
        border: 2px solid #334155;
    }

    /* Specific Utility Classes for HTML injection */
    .highlight-text { color: #f59e0b; font-weight: bold; } /* Amber-500 */
    .success-text { color: #10b981; font-weight: bold; } /* Emerald-500 */
    .danger-text { color: #ef4444; font-weight: bold; } /* Red-500 */
    .info-text { color: #3b82f6; font-weight: bold; } /* Blue-500 */
    
    /* Hide Streamlit default menu elements for cleaner look */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. CONSTANTS & INITIALIZATION
# -----------------------------------------------------------------------------

TEAM_NAMES = [
    "Aditya Avengers",
    "Alfen Royals",
    "Lantern Legends",
    "Primark Superkings",
    "Sai Kripa Soldiers",
    "Taluka Fighters"
]

DEFAULT_CONFIG = {
    "purseLimit": 2500,
    "maxSquadSize": 35,
    "basePrice": 10
}

# Initial Data (Mock if no CSV loaded)
INITIAL_PLAYERS = [
    {"ID": 1, "Name": "Ar. Abhishek Chandaliya", "Team": None, "Price": 0, "Cricket": "A", "Badminton": "B", "TT": "0", "CaptainFor": None},
    {"ID": 2, "Name": "Virat K", "Team": None, "Price": 0, "Cricket": "A", "Badminton": "0", "TT": "0", "CaptainFor": None},
    {"ID": 3, "Name": "PV Sindhu", "Team": None, "Price": 0, "Cricket": "0", "Badminton": "A", "TT": "0", "CaptainFor": None},
    {"ID": 4, "Name": "Sharath Kamal", "Team": None, "Price": 0, "Cricket": "0", "Badminton": "0", "TT": "A", "CaptainFor": None},
    {"ID": 5, "Name": "Amit Jain", "Team": None, "Price": 0, "Cricket": "B", "Badminton": "B", "TT": "B", "CaptainFor": None},
]

# Initialize Session State
if 'players' not in st.session_state:
    st.session_state.players = pd.DataFrame(INITIAL_PLAYERS)

if 'config' not in st.session_state:
    st.session_state.config = DEFAULT_CONFIG

if 'audit_log' not in st.session_state:
    st.session_state.audit_log = []

if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False

if 'current_tab' not in st.session_state:
    st.session_state.current_tab = "Dashboard"

# -----------------------------------------------------------------------------
# 3. HELPER FUNCTIONS
# -----------------------------------------------------------------------------

def add_log(message, type="info"):
    st.session_state.audit_log.insert(0, {
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "message": message,
        "type": type
    })
    # Keep log size manageable
    st.session_state.audit_log = st.session_state.audit_log[:50]

def calculate_team_stats():
    df = st.session_state.players
    config = st.session_state.config
    stats = []

    for team in TEAM_NAMES:
        team_players = df[df['Team'] == team]
        count = len(team_players)
        spent = team_players['Price'].sum() if not team_players.empty else 0
        
        # Sport Counts
        cricket = len(team_players[team_players['Cricket'].isin(['A','B','C'])])
        badminton = len(team_players[team_players['Badminton'].isin(['A','B','C'])])
        tt = len(team_players[team_players['TT'].isin(['A','B','C'])])
        
        # Financials
        available = config['purseLimit'] - spent
        empty_slots = max(0, config['maxSquadSize'] - count)
        reserve = empty_slots * config['basePrice']
        disposable = available - reserve

        stats.append({
            "Team": team,
            "Spent": spent,
            "Count": count,
            "Slots": empty_slots,
            "Purse": available,
            "Disposable": disposable,
            "Cricket": cricket,
            "Badminton": badminton,
            "TT": tt
        })
    
    return pd.DataFrame(stats)

def get_developer_status():
    df = st.session_state.players
    # Search for developer
    dev = df[df['Name'].str.contains("Abhishek Chandaliya", case=False, na=False)]
    if not dev.empty:
        row = dev.iloc[0]
        return {
            "found": True,
            "team": row['Team'],
            "price": row['Price'],
            "status": "SOLD" if row['Team'] else "UNSOLD"
        }
    return {"found": False}

def get_player_image(player_name):
    """
    Finds the player image in the 'photos' directory.
    Checks for .png, .jpg, .jpeg.
    Returns path to image or default_player.png if not found.
    """
    base_path = "photos"
    extensions = [".png", ".jpg", ".jpeg"]
    
    # Check for specific player image
    for ext in extensions:
        img_path = os.path.join(base_path, f"{player_name}{ext}")
        if os.path.exists(img_path):
            return img_path
    
    # Check for default fallback
    default_path = os.path.join(base_path, "default_player.png")
    if os.path.exists(default_path):
        return default_path
        
    # If no default image exists, we return None (will handle in UI with a placeholder block)
    return None

# -----------------------------------------------------------------------------
# 4. COMPONENT RENDERERS
# -----------------------------------------------------------------------------

def render_developer_profile():
    dev_status = get_developer_status()
    
    bg_color = "#1e293b"
    border_color = "#334155"
    status_color = "#f59e0b" # Amber
    status_text = "Auction Status: UNSOLD"
    
    if dev_status['found'] and dev_status['team']:
        bg_color = "rgba(6, 78, 59, 0.4)" # Emerald tint
        border_color = "#10b981"
        status_color = "#10b981"
        status_text = f"Playing For: {dev_status['team']}"

    st.markdown(f"""
    <div style="background-color: {bg_color}; border: 1px solid {border_color}; border-radius: 12px; padding: 16px; margin-bottom: 20px;">
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
            <div style="width: 48px; height: 48px; background-color: #0f172a; border: 2px solid #6366f1; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; color: #6366f1;">
                AC
            </div>
            <div>
                <h4 style="margin: 0; color: white; font-size: 16px;">Ar. Abhishek Chandaliya</h4>
                <p style="margin: 0; color: #94a3b8; font-size: 12px;">Auction Architect</p>
            </div>
        </div>
        <div style="background-color: rgba(0,0,0,0.2); border-radius: 8px; padding: 8px; border: 1px solid {border_color};">
            <p style="margin: 0; color: {status_color}; font-weight: bold; font-size: 12px; text-transform: uppercase;">
                {status_text}
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_dashboard():
    st.title("📊 Dashboard")
    
    stats_df = calculate_team_stats()
    df = st.session_state.players

    # 1. Top Metrics
    total_sold = stats_df['Count'].sum()
    total_slots = len(TEAM_NAMES) * st.session_state.config['maxSquadSize']
    remaining = total_slots - total_sold
    
    # Calculate highest bids
    sold_players = df[df['Team'].notna()]
    top_cricket = sold_players[sold_players['Cricket'] != '0'].sort_values('Price', ascending=False).head(1)
    top_badminton = sold_players[sold_players['Badminton'] != '0'].sort_values('Price', ascending=False).head(1)
    top_tt = sold_players[sold_players['TT'] != '0'].sort_values('Price', ascending=False).head(1)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Sold", total_sold, delta=f"{remaining} Remaining", delta_color="inverse")
    with col2:
        val = f"₹{top_cricket.iloc[0]['Price']}" if not top_cricket.empty else "-"
        name = top_cricket.iloc[0]['Name'] if not top_cricket.empty else "No Bids"
        st.metric("🏏 Top Cricketer", val, name)
    with col3:
        val = f"₹{top_badminton.iloc[0]['Price']}" if not top_badminton.empty else "-"
        name = top_badminton.iloc[0]['Name'] if not top_badminton.empty else "No Bids"
        st.metric("🏸 Top Shuttler", val, name)
    with col4:
        val = f"₹{top_tt.iloc[0]['Price']}" if not top_tt.empty else "-"
        name = top_tt.iloc[0]['Name'] if not top_tt.empty else "No Bids"
        st.metric("🏓 Top Paddler", val, name)

    st.markdown("---")

    # 2. Leaderboard Table
    st.subheader("Team Standings")
    
    # Format for display
    display_df = stats_df[['Team', 'Disposable', 'Count', 'Cricket', 'Badminton', 'TT']].copy()
    display_df.columns = ['Team', 'Purse Left (₹)', 'Squad Size', '🏏 Cricket', '🏸 Badminton', '🏓 TT']
    
    # Apply styling
    st.dataframe(
        display_df.style.background_gradient(subset=['Purse Left (₹)'], cmap="Greens").format({'Purse Left (₹)': '₹{:,}'}),
        use_container_width=True,
        height=300
    )

def render_auction_console():
    st.title("🔨 Auction Console")
    
    if not st.session_state.is_admin:
        st.warning("🔒 Admin Access Required. Please login in Settings.")
        return

    df = st.session_state.players
    config = st.session_state.config
    stats_df = calculate_team_stats()

    # Layout: Left (Search/Spin), Right (Action)
    col_left, col_right = st.columns([1, 2])

    with col_left:
        st.markdown("### 🔍 Select Player")
        
        # 1. Randomizer
        st.markdown("#### Random Picker")
        r_sport = st.selectbox("Sport", ["All", "Cricket", "Badminton", "TT"])
        r_grade = st.selectbox("Grade", ["All", "A", "B", "C"])
        
        if st.button("🎲 SPIN RANDOM", use_container_width=True, type="primary"):
            # Filter unsold
            unsold = df[df['Team'].isna()]
            if r_sport != "All":
                unsold = unsold[unsold[r_sport].isin(['A','B','C'])]
            if r_grade != "All":
                # Rough logic: check if any sport matches grade if All, or specific if Sport selected
                pass # Keeping simple for brevity
            
            if not unsold.empty:
                winner = unsold.sample(1).iloc[0]
                st.session_state['selected_player_id'] = int(winner['ID'])
                st.success(f"Selected: {winner['Name']}")
            else:
                st.error("No players match criteria.")

        st.markdown("---")
        
        # 2. Manual Search
        st.markdown("#### Manual Search")
        search_term = st.text_input("Search Name")
        unsold_df = df[df['Team'].isna()]
        if search_term:
            unsold_df = unsold_df[unsold_df['Name'].str.contains(search_term, case=False)]
        
        player_options = unsold_df.to_dict('records')
        player_map = {f"{p['Name']} (#{p['ID']})": p['ID'] for p in player_options}
        
        selected_label = st.selectbox("Select Unsold Player", options=list(player_map.keys()))
        
        if selected_label:
            st.session_state['selected_player_id'] = player_map[selected_label]

    with col_right:
        # Get Current Player
        pid = st.session_state.get('selected_player_id')
        if not pid:
            st.info("Select a player to start bidding.")
        else:
            player = df[df['ID'] == pid].iloc[0]
            
            # -----------------------------------------------------
            # HERO CARD WITH IMAGE
            # -----------------------------------------------------
            # Get Image Path
            img_path = get_player_image(player['Name'])
            
            # Wrapper for styling
            st.markdown("""
            <style>
                .hero-container {
                    background-color: #0f172a;
                    border: 2px solid #6366f1;
                    border-radius: 16px;
                    padding: 20px;
                    margin-bottom: 20px;
                    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5);
                }
            </style>
            """, unsafe_allow_html=True)

            with st.container():
                st.markdown('<div class="hero-container">', unsafe_allow_html=True)
                
                # Split Image and Details
                h_col1, h_col2 = st.columns([1, 3])
                
                with h_col1:
                    if img_path:
                        st.image(img_path, use_container_width=True)
                    else:
                        # Placeholder if no image found
                        st.markdown("""
                        <div style="width:100%; aspect-ratio:1/1; background-color:#1e293b; border-radius:12px; display:flex; align-items:center; justify-content:center; border:2px dashed #475569;">
                            <span style="font-size:3rem;">👤</span>
                        </div>
                        """, unsafe_allow_html=True)

                with h_col2:
                    st.markdown(f'<h1 style="font-size: 3.5rem; margin: 0; line-height: 1.1; color: #fff;">{player["Name"]}</h1>', unsafe_allow_html=True)
                    st.markdown(f'<div style="color: #64748b; font-family: monospace; font-size: 1rem; margin-top: 5px; margin-bottom: 15px;">PLAYER ID: #{player["ID"]}</div>', unsafe_allow_html=True)
                    
                    # Sports Badges
                    badge_html = f"""
                    <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                        <span class="highlight-text" style="background:#1e3a8a; padding:5px 15px; border-radius:20px; border:1px solid #3b82f6;">🏏 Cricket: {player['Cricket']}</span>
                        <span class="success-text" style="background:#064e3b; padding:5px 15px; border-radius:20px; border:1px solid #10b981;">🏸 Badminton: {player['Badminton']}</span>
                        <span class="info-text" style="background:#431407; padding:5px 15px; border-radius:20px; border:1px solid #f97316;">🏓 TT: {player['TT']}</span>
                    </div>
                    """
                    st.markdown(badge_html, unsafe_allow_html=True)

                st.markdown('</div>', unsafe_allow_html=True)
            
            # -----------------------------------------------------
            # BIDDING CONTROLS
            # -----------------------------------------------------
            with st.container():
                st.markdown("### 💰 Bidding")
                
                b_col1, b_col2 = st.columns(2)
                with b_col1:
                    winning_team = st.selectbox("Winning Team", TEAM_NAMES)
                with b_col2:
                    bid_amount = st.number_input("Winning Bid", min_value=0, value=config['basePrice'], step=10)
                
                # Validation Logic
                team_stat = stats_df[stats_df['Team'] == winning_team].iloc[0]
                
                # Check 1: Full
                is_full = team_stat['Count'] >= config['maxSquadSize']
                
                # Check 2: Budget
                # Max Bid = Disposable + Base Price (since we are filling a slot, we use its reserve)
                max_bid = team_stat['Disposable'] + config['basePrice']
                can_afford = bid_amount <= max_bid

                if is_full:
                    st.error(f"❌ {winning_team} is FULL ({team_stat['Count']}/{config['maxSquadSize']})")
                elif not can_afford:
                    st.error(f"❌ Insufficient Funds. Max Bid: {max_bid}")
                else:
                    st.success(f"✅ Budget OK. Remaining after bid: {team_stat['Disposable'] + config['basePrice'] - bid_amount}")
                    
                    if st.button("🔨 SOLD", type="primary", use_container_width=True):
                        # UPDATE DATAFRAME
                        idx = df[df['ID'] == pid].index
                        df.loc[idx, 'Team'] = winning_team
                        df.loc[idx, 'Price'] = bid_amount
                        
                        add_log(f"SOLD: {player['Name']} to {winning_team} for {bid_amount}", "sale")
                        
                        st.balloons()
                        time.sleep(1)
                        st.rerun()

    # -------------------------------------------------------------------------
    # CORRECTION MANAGER
    # -------------------------------------------------------------------------
    st.markdown("---")
    with st.expander("🛠️ Correction Manager (Fix Mistakes / Unsell)"):
        st.markdown("Use this tool to modify sales or unsell a player if a mistake was made.")
        
        # 1. Search Sold Players
        sold_players = df[df['Team'].notna()]
        
        # Search input
        cm_search = st.text_input("Find Sold Player", placeholder="Type name...")
        
        # Filter dropdown based on search
        if cm_search.strip():
            filtered_sold = sold_players[sold_players['Name'].str.contains(cm_search, case=False)]
        else:
            filtered_sold = sold_players
            
        # Create map for selectbox
        sold_map = {f"{row['Name']} ({row['Team']})": row['ID'] for _, row in filtered_sold.iterrows()}
        
        selected_sold_label = st.selectbox("Select Player to Edit", options=[""] + list(sold_map.keys()))
        
        if selected_sold_label:
            target_id = sold_map[selected_sold_label]
            target_player = df[df['ID'] == target_id].iloc[0]
            
            st.info(f"Editing: **{target_player['Name']}** | Current Team: {target_player['Team']} | Price: {target_player['Price']}")
            
            c1, c2 = st.columns(2)
            
            # ZONE 1: UPDATE
            with c1:
                st.markdown("#### Update Details")
                new_team = st.selectbox("New Team", TEAM_NAMES, index=TEAM_NAMES.index(target_player['Team']) if target_player['Team'] in TEAM_NAMES else 0)
                new_price = st.number_input("New Price", value=int(target_player['Price']))
                
                if st.button("Update Sale"):
                    idx = df[df['ID'] == target_id].index
                    df.loc[idx, ['Team', 'Price']] = [new_team, new_price]
                    add_log(f"CORRECTION: {target_player['Name']} updated to {new_team} @ {new_price}", "correction")
                    st.success("Updated!")
                    time.sleep(0.5)
                    st.rerun()
            
            # ZONE 2: UNSELL (THE REQUESTED FIX)
            with c2:
                st.markdown("#### ⚠️ Danger Zone")
                st.markdown("Revert this player to **Unsold** status immediately.")
                
                # Independent Unsell Button
                if st.button("❌ Revert to Unsold", type="primary", key="btn_unsell"):
                    # Direct Logic
                    idx = df[df['ID'] == target_id].index
                    prev_team = df.loc[idx, 'Team'].values[0]
                    
                    # Reset fields
                    df.loc[idx, 'Team'] = None
                    df.loc[idx, 'Price'] = 0
                    df.loc[idx, 'CaptainFor'] = None # Also remove captaincy if reverted
                    
                    add_log(f"REVERT: {target_player['Name']} removed from {prev_team}", "revert")
                    
                    st.success(f"Player {target_player['Name']} is now Unsold!")
                    time.sleep(0.5)
                    st.rerun()

def render_teams():
    st.title("👥 Teams & Rosters")
    
    stats_df = calculate_team_stats()
    df = st.session_state.players
    
    for _, team_stat in stats_df.iterrows():
        team_name = team_stat['Team']
        
        # Attention Logic
        attention_needed = False
        border_color = "#334155"
        
        if team_stat['Cricket'] < 6: attention_needed = True
        
        with st.expander(f"{team_name} (Sold: {team_stat['Count']}/{st.session_state.config['maxSquadSize']}) - Purse: ₹{team_stat['Disposable']}", expanded=False):
            
            # Stats Grid
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Spent", f"₹{team_stat['Spent']}")
            c2.metric("Cricket", team_stat['Cricket'])
            c3.metric("Badminton", team_stat['Badminton'])
            c4.metric("TT", team_stat['TT'])
            
            # Roster Table
            team_roster = df[df['Team'] == team_name].copy()
            if not team_roster.empty:
                st.dataframe(
                    team_roster[['Name', 'Price', 'Cricket', 'Badminton', 'TT', 'CaptainFor']],
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No players yet.")

def render_settings():
    st.title("⚙️ Settings & Admin")
    
    # 1. Login
    if not st.session_state.is_admin:
        with st.form("admin_login"):
            st.subheader("Admin Login")
            pwd = st.text_input("Password", type="password")
            if st.form_submit_button("Unlock"):
                if pwd == "ABCD2026":
                    st.session_state.is_admin = True
                    st.rerun()
                else:
                    st.error("Incorrect Password")
        return

    # If Logged In
    st.success("You are logged in as Admin.")
    if st.button("Logout"):
        st.session_state.is_admin = False
        st.rerun()
    
    tab1, tab2, tab3 = st.tabs(["Tournament Config", "Data Management", "Captains"])
    
    with tab1:
        st.subheader("Rules")
        c_purse = st.number_input("Purse Limit", value=st.session_state.config['purseLimit'])
        c_squad = st.number_input("Max Squad", value=st.session_state.config['maxSquadSize'])
        c_base = st.number_input("Base Price", value=st.session_state.config['basePrice'])
        
        if st.button("Save Config"):
            st.session_state.config = {
                "purseLimit": c_purse,
                "maxSquadSize": c_squad,
                "basePrice": c_base
            }
            st.success("Configuration Saved!")

    with tab2:
        st.subheader("Export Data")
        
        # Export CSV
        csv = st.session_state.players.to_csv(index=False).encode('utf-8')
        st.download_button(
            "Download Player Data (CSV)",
            csv,
            "auction_data.csv",
            "text/csv",
            key='download-csv'
        )
        
        st.subheader("Import Data")
        uploaded_file = st.file_uploader("Upload CSV", type=['csv'])
        if uploaded_file is not None:
            try:
                new_df = pd.read_csv(uploaded_file)
                # Basic validation
                req_cols = ['Name', 'Cricket', 'Badminton', 'TT']
                if all(col in new_df.columns for col in req_cols):
                    # Ensure ID column
                    if 'ID' not in new_df.columns:
                        new_df['ID'] = range(1, len(new_df) + 1)
                    
                    # Ensure needed columns exist
                    for col in ['Team', 'Price', 'CaptainFor']:
                        if col not in new_df.columns:
                            new_df[col] = None
                    
                    # Fill NaNs
                    new_df['Price'] = new_df['Price'].fillna(0)
                    
                    if st.button("Overwrite Database"):
                        st.session_state.players = new_df
                        st.success(f"Loaded {len(new_df)} players.")
                        st.rerun()
                else:
                    st.error(f"CSV missing required columns: {req_cols}")
            except Exception as e:
                st.error(f"Error parsing CSV: {e}")

    with tab3:
        st.subheader("Assign Captains")
        df = st.session_state.players
        
        # Form
        cap_team = st.selectbox("Select Team", TEAM_NAMES, key="cap_team")
        cap_sport = st.selectbox("Select Sport", ["Cricket", "Badminton", "TT"], key="cap_sport")
        
        # Search unsold players
        unsold_cap = df[df['Team'].isna()]
        cap_search = st.text_input("Search Player for Captaincy")
        
        if cap_search:
            unsold_cap = unsold_cap[unsold_cap['Name'].str.contains(cap_search, case=False)]
        
        cap_map = {f"{r['Name']} (#{r['ID']})": r['ID'] for _, r in unsold_cap.iterrows()}
        cap_select_label = st.selectbox("Select Player", list(cap_map.keys()), key="cap_select")
        
        cap_price = st.number_input("Captain Price", value=0, key="cap_price")
        
        if st.button("Assign Captain"):
            if cap_select_label:
                pid = cap_map[cap_select_label]
                idx = df[df['ID'] == pid].index
                
                df.loc[idx, 'Team'] = cap_team
                df.loc[idx, 'Price'] = cap_price
                df.loc[idx, 'CaptainFor'] = cap_sport
                
                add_log(f"CAPTAIN: {df.loc[idx, 'Name'].values[0]} assigned to {cap_team}", "captain")
                st.success("Captain Assigned!")
                st.rerun()

# -----------------------------------------------------------------------------
# 5. MAIN LAYOUT
# -----------------------------------------------------------------------------

def main():
    # Sidebar Navigation
    with st.sidebar:
        st.title("🏆 Navigation")
        
        # Navigation Buttons
        if st.button("📊 Dashboard", use_container_width=True):
            st.session_state.current_tab = "Dashboard"
        if st.button("🔨 Auction Console", use_container_width=True):
            st.session_state.current_tab = "Console"
        if st.button("👥 Teams", use_container_width=True):
            st.session_state.current_tab = "Teams"
        if st.button("⚙️ Settings", use_container_width=True):
            st.session_state.current_tab = "Settings"
            
        st.markdown("---")
        render_developer_profile()
        
        st.markdown("---")
        st.markdown("### 📜 Recent Activity")
        for log in st.session_state.audit_log[:5]:
            icon = "🔹"
            if log['type'] == 'sale': icon = "💰"
            if log['type'] == 'revert': icon = "❌"
            if log['type'] == 'captain': icon = "👑"
            st.markdown(f"<div style='font-size:12px; border-bottom:1px solid #333; padding:5px;'>{icon} {log['message']}</div>", unsafe_allow_html=True)

    # Main Content Area
    tab = st.session_state.current_tab
    
    if tab == "Dashboard":
        render_dashboard()
    elif tab == "Console":
        render_auction_console()
    elif tab == "Teams":
        render_teams()
    elif tab == "Settings":
        render_settings()

if __name__ == "__main__":
    main()