import streamlit as st
import pandas as pd
import sqlite3
import sys
import os
import subprocess
import re
import html

# Add project root to Python path so Streamlit can find the 'app' module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db import get_connection, init_db
from app.config import DB_PATH
from app.parser import fetch_release_notes
from app.scorer import evaluate_event

# Set up the wide layout for the dashboard
st.set_page_config(page_title="GCP Release Intel", page_icon="☁️", layout="wide")

# --- UI HELPERS & ENHANCEMENTS ---

HIGHLIGHT_TIERS = {
    "critical": {
        "color": "#ff4b4b",
        "bg": "#2d0000",
        "keywords": [
            "breaking change", "deprecated", "removed", "end of life",
            "EOL", "disable", "revoked", "breach", "mandatory migration"
        ],
    },
    "high": {
        "color": "#ffa500",
        "bg": "#2b1a00",
        "keywords": [
            "IAM", "RBAC", "privilege", "permission", "firewall", "VPC",
            "encryption", "CMEK", "KMS", "secret", "vulnerability", "CVE",
            "org policy", "constraint", "audit log", "security command center",
            "privilege escalation"
        ],
    },
    "medium": {
        "color": "#3dd68c",
        "bg": "#001f12",
        "keywords": [
            "preview", "GA", "generally available", "public preview",
            "workload identity", "service account", "token", "mTLS",
        ],
    },
}

def highlight_keywords(text: str) -> str:
    """Wraps security keywords in inline HTML spans with color-coded highlighting."""
    text = html.escape(text)
    for tier, config in HIGHLIGHT_TIERS.items():
        sorted_kws = sorted(config["keywords"], key=len, reverse=True)
        pattern = r'\b(' + '|'.join(re.escape(kw) for kw in sorted_kws) + r')\b'
        replacement = (
            f'<span style="color:{config["color"]}; background:{config["bg"]}; '
            f'font-weight:700; padding:1px 5px; border-radius:4px; '
            f'font-family:monospace; font-size:0.9em;">\\1</span>'
        )
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text

def render_metric_cards(df):
    """Renders 4 KPI cards at the top of the dashboard."""
    total = len(df)
    high_risk = len(df[df["final_score"] >= 5.0])
    # Dynamically detect security items by checking if raw_text contains our major keywords
    security_items = len(df[df["raw_text"].str.contains("security|iam|firewall|armor|vpc|kms|cmek", case=False, na=False)])
    discarded = len(df[df["final_score"] == -1.0])

    st.markdown("""
    <style>
    [data-testid="stMetricValue"] {
        font-size: 2.4rem !important;
        font-weight: 800 !important;
        letter-spacing: -1px;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.85rem !important;
        text-transform: uppercase;
        letter-spacing: 1px;
        opacity: 0.75;
    }
    div[data-testid="metric-container"] {
        background: #0f1117;
        border: 1px solid #2a2d3e;
        border-radius: 10px;
        padding: 18px 24px;
    }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(label="🚨 High-Risk Updates", value=high_risk, delta=f"{round(high_risk/total*100)}% of total" if total else "—", delta_color="inverse")
    with col2:
        st.metric(label="🔒 Security Events", value=security_items)
    with col3:
        st.metric(label="📦 Total Parsed", value=total)
    with col4:
        st.metric(label="🗑️ Discarded (Noise)", value=discarded, delta_color="off")

def render_ai_prep_block(row):
    """Renders a reserved AI TL;DR section inside a release note expander."""
    tldr = row.get("ai_summary", "")
    st.markdown("&nbsp;", unsafe_allow_html=True)

    if tldr:
        st.markdown(
            f"""
            <div style="border-left: 4px solid #3dd68c; background: #001f12; padding: 12px 16px; border-radius: 0 8px 8px 0; margin-top: 8px;">
                <div style="font-size: 0.7em; text-transform: uppercase; letter-spacing: 1.5px; color: #3dd68c; font-weight: 700; margin-bottom: 6px;">🤖 AI TL;DR</div>
                <div style="color: #e8f5e9; font-size: 0.95em; line-height: 1.5;">{html.escape(tldr)}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown(
            """
            <div style="border: 1.5px dashed #2a2d3e; background: #0a0c12; padding: 10px 16px; border-radius: 8px; margin-top: 8px; opacity: 0.6;">
                <div style="font-size: 0.7em; text-transform: uppercase; letter-spacing: 1.5px; color: #555; font-weight: 700; margin-bottom: 4px;">🤖 AI TL;DR</div>
                <div style="color: #444; font-size: 0.88em; font-style: italic;">— Pending generation —</div>
            </div>
            """, unsafe_allow_html=True)

def render_note_card(row):
    """Renders a single release note inside an expander with score badge."""
    score = row.get("final_score", 0.0)
    score_color = "#ff4b4b" if score >= 5.0 else "#ffa500" if score > 0 else "#888"
    icon = "🔥" if score >= 5.0 else "🟢" if score > 0 else "🗑️"
    
    score_badge = (
        f'<span style="background:{score_color}; color:#fff; font-weight:700; '
        f'padding:2px 8px; border-radius:12px; font-size:0.8em; '
        f'font-family:monospace;">Score: {score:.2f}</span>'
    )

    label = f"{icon} {row['service']} | {row['category']} | {row['published_date'][:10]}"
    with st.expander(label, expanded=(score >= 5.0)):
        st.markdown(score_badge, unsafe_allow_html=True)
        st.markdown("---")
        
        st.markdown(highlight_keywords(row.get("raw_text", "")), unsafe_allow_html=True)
        
        # Render AI TL;DR block
        render_ai_prep_block(row)

        # Render Documentation Links
        if row.get('doc_links'):
            st.markdown("<br>", unsafe_allow_html=True)
            links = row['doc_links'].split(",")
            cols = st.columns(len(links) + 5)
            for i, link in enumerate(links):
                with cols[i]:
                    st.markdown(f"<a href='{link}' target='_blank'><button style='background-color:#2a2d3e; border:1px solid #444; color:white; border-radius:4px; padding:4px 8px; cursor:pointer;'>📘 Docs</button></a>", unsafe_allow_html=True)

def render_swimlanes(df: pd.DataFrame):
    """Groups df by category and renders each group in its own tab."""
    TAB_CONFIG = {
        "Feature": "✨ Features",
        "Update": "🔄 Updates",
        "Deprecated": "🪦 Deprecations",
        "Announcement": "📢 Announcements",
        "Breaking Change": "⚠️ Breaking Changes",
        "General": "📦 General",
    }
    
    if "category" not in df.columns:
        df["category"] = "General"
    df["category"] = df["category"].fillna("General")

    present_cats = df["category"].unique().tolist()
    ordered = [c for c in TAB_CONFIG if c in present_cats]
    extras  = [c for c in present_cats if c not in TAB_CONFIG]
    all_cats = ordered + extras

    tab_labels = [TAB_CONFIG.get(c, f"📄 {c}") for c in all_cats]
    
    if not tab_labels:
        st.warning("No events to display.")
        return
        
    tabs = st.tabs(tab_labels)

    for tab, cat in zip(tabs, all_cats):
        with tab:
            subset = df[df["category"] == cat].sort_values("final_score", ascending=False)
            st.caption(f"{len(subset)} events · sorted by score ↓")
            for _, row in subset.iterrows():
                render_note_card(row)

# --- CORE PIPELINE LOGIC ---

def run_pipeline():
    """Runs the Parse and Score stages and updates the UI."""
    init_db()
    
    with st.spinner("Fetching and parsing new release notes..."):
        events = fetch_release_notes(days_back=10)
        inserted = 0
        with get_connection() as conn:
            cursor = conn.cursor()
            for event in events:
                try:
                    cursor.execute("""
                        INSERT INTO release_note_events 
                        (service, published_date, raw_text, source_url, doc_links, event_hash, category, published_week)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (event.service, event.published_date, event.raw_text, event.source_url, event.doc_links, event.event_hash, event.category, event.published_week))
                    inserted += 1
                except sqlite3.IntegrityError:
                    pass # Skip duplicates
            conn.commit()
            
    with st.spinner("Running deterministic scoring engine..."):
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, service, raw_text FROM release_note_events WHERE final_score = 0")
            rows = cursor.fetchall()
            scored = 0
            for row in rows:
                r_score, p_score, f_score = evaluate_event(row["service"], row["raw_text"])
                cursor.execute("UPDATE release_note_events SET rule_score = ?, popularity_score = ?, final_score = ? WHERE id = ?", 
                               (r_score, p_score, f_score, row["id"]))
                scored += 1
            conn.commit()
            
    st.success(f"✅ Pipeline Complete! Ingested {inserted} new events and scored {scored} items.")

# --- SIDEBAR CONTROLS ---
st.sidebar.title("☁️ GCP Intel Control")

if st.sidebar.button("🚀 Run Parse & Score", use_container_width=True):
    run_pipeline()

st.sidebar.markdown("---")
st.sidebar.subheader("☢️ Danger Zone")

# Guard with a confirm toggle
confirm_reset = st.sidebar.checkbox("🔓 Unlock Nuclear Reset", value=False)
if confirm_reset:
    if st.sidebar.button("☢️ Nuclear Reset", type="primary", use_container_width=True):
        with st.status("Running Nuclear Reset...", expanded=True) as status:
            st.write("🗑️ Deleting database...")
            if os.path.exists(DB_PATH):
                os.remove(DB_PATH)
            st.write("✅ Database wiped.")
            
            st.write("⚙️ Running parser...")
            result = subprocess.run([sys.executable, "-m", "app.main", "parse"], capture_output=True, text=True)
            if result.returncode != 0:
                st.error(f"Parse failed:\n{result.stderr}")
                status.update(label="❌ Reset failed at parse.", state="error")
                st.stop()
                
            st.write("🧮 Running scorer...")
            result = subprocess.run([sys.executable, "-m", "app.main", "score"], capture_output=True, text=True)
            if result.returncode != 0:
                st.error(f"Score failed:\n{result.stderr}")
                status.update(label="❌ Reset failed at score.", state="error")
                st.stop()
                
            status.update(label="☢️ Nuclear Reset Complete. Reloading...", state="complete")
        st.rerun()
else:
    st.sidebar.button("☢️ Nuclear Reset", disabled=True, use_container_width=True, help="Check the box above to unlock.")

st.sidebar.markdown("---")
st.sidebar.subheader("Filters")

# Load Data
with get_connection() as conn:
    df = pd.read_sql_query("""
        SELECT service, category, final_score, published_date, raw_text, doc_links, ai_summary 
        FROM release_note_events 
        ORDER BY published_date DESC
    """, conn)

if df.empty:
    st.warning("No data found in the database. Click 'Run Parse & Score' to start!")
    st.stop()

# Filter Widgets
view_mode = st.sidebar.radio("View Mode", ["🏆 Shortlist (Score > 0)", "👀 All Events (Including Junk)"])

services_list = sorted(df['service'].unique().tolist())
selected_services = st.sidebar.multiselect("Filter by Service", services_list)

# Apply Filters
filtered_df = df.copy()

if view_mode == "🏆 Shortlist (Score > 0)":
    filtered_df = filtered_df[filtered_df['final_score'] > 0]
    filtered_df = filtered_df.sort_values(by="final_score", ascending=False) # Highest scores first

if selected_services:
    filtered_df = filtered_df[filtered_df['service'].isin(selected_services)]

# --- MAIN CONTENT AREA ---
st.title(f"Release Notes Dashboard ({len(filtered_df)} Events)")

# Render the top-level metric glance cards
render_metric_cards(df)
st.markdown("---")

# Render the swimlane tabs and filtered expander cards
render_swimlanes(filtered_df)