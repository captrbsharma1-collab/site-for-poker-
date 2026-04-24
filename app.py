"""
app.py — Streamlit front-end for the Poker Decision Support Tool
Place this file in the same folder as observer.py, state.py, engine.py
Run with: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import sys, os

# ── allow imports from same directory ─────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))
from observer import Observer
from state import GameState
from engine import PokerEngine, OpponentClassifier, TiltDetector

# ══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Poker DST",
    page_icon="♠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════════════════════
# CUSTOM CSS  — dark felt theme
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
/* ── Base ── */
html, body, [data-testid="stAppViewContainer"] {
    background-color: #0d1f12;
    color: #e8e0d0;
    font-family: 'Georgia', serif;
}
[data-testid="stSidebar"] {
    background-color: #091508;
    border-right: 1px solid #2a4a2a;
}
[data-testid="stSidebar"] * { color: #c8d8c0 !important; }

/* ── Cards / panels ── */
.card {
    background: #122018;
    border: 1px solid #2a4a30;
    border-radius: 10px;
    padding: 18px 22px;
    margin-bottom: 14px;
}
.card-red {
    background: #1f0d0d;
    border: 1px solid #7a2020;
    border-radius: 10px;
    padding: 18px 22px;
    margin-bottom: 14px;
}
.card-gold {
    background: #1a1608;
    border: 1px solid #7a6010;
    border-radius: 10px;
    padding: 18px 22px;
    margin-bottom: 14px;
}

/* ── Section headings ── */
.section-title {
    font-size: 0.72rem;
    font-family: 'Courier New', monospace;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: #4a8a50;
    margin-bottom: 10px;
}
.panel-title {
    font-size: 1.05rem;
    font-weight: bold;
    color: #d4b96a;
    margin-bottom: 6px;
}

/* ── Profile badge ── */
.profile-badge {
    display: inline-block;
    background: #1e3a22;
    border: 1px solid #3a7a40;
    border-radius: 20px;
    padding: 4px 14px;
    font-size: 0.85rem;
    color: #80d890;
    margin-right: 8px;
    margin-bottom: 6px;
}
.profile-badge-red {
    display: inline-block;
    background: #3a1010;
    border: 1px solid #8a2020;
    border-radius: 20px;
    padding: 4px 14px;
    font-size: 0.85rem;
    color: #e07070;
    margin-right: 8px;
    margin-bottom: 6px;
}
.profile-badge-gold {
    display: inline-block;
    background: #2e2408;
    border: 1px solid #9a8020;
    border-radius: 20px;
    padding: 4px 14px;
    font-size: 0.85rem;
    color: #d4b96a;
    margin-right: 8px;
    margin-bottom: 6px;
}

/* ── Tilt banner ── */
.tilt-banner {
    background: linear-gradient(90deg, #3a0808 0%, #1f0505 100%);
    border: 1px solid #cc2222;
    border-radius: 8px;
    padding: 12px 18px;
    color: #ff8080;
    font-size: 0.95rem;
    margin-bottom: 12px;
}
.tilt-banner-mod {
    background: linear-gradient(90deg, #3a2008 0%, #1f1205 100%);
    border: 1px solid #cc8822;
    border-radius: 8px;
    padding: 12px 18px;
    color: #ffc080;
    font-size: 0.95rem;
    margin-bottom: 12px;
}

/* ── Insight bullet ── */
.insight-row {
    border-left: 3px solid #3a7a40;
    padding: 6px 0 6px 12px;
    margin-bottom: 8px;
    color: #c8d8c0;
    font-size: 0.9rem;
    line-height: 1.5;
}
.insight-row-warn {
    border-left: 3px solid #cc8822;
    padding: 6px 0 6px 12px;
    margin-bottom: 8px;
    color: #ffc080;
    font-size: 0.9rem;
    line-height: 1.5;
}
.insight-row-danger {
    border-left: 3px solid #cc2222;
    padding: 6px 0 6px 12px;
    margin-bottom: 8px;
    color: #ff8080;
    font-size: 0.9rem;
    line-height: 1.5;
}

/* ── Stat numbers ── */
.stat-big {
    font-size: 2rem;
    font-weight: bold;
    color: #d4b96a;
    line-height: 1;
}
.stat-label {
    font-size: 0.68rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #4a8a50;
}

/* ── EV pill ── */
.ev-positive { color: #60e870; font-weight: bold; font-size: 1rem; }
.ev-neutral  { color: #e8c840; font-weight: bold; font-size: 1rem; }
.ev-negative { color: #e84040; font-weight: bold; font-size: 1rem; }

/* ── Action log ── */
.log-entry {
    font-family: 'Courier New', monospace;
    font-size: 0.78rem;
    color: #8aaa80;
    padding: 2px 0;
    border-bottom: 1px solid #1a2e1a;
}

/* ── Streamlit overrides ── */
.stButton > button {
    background: #1a3020;
    border: 1px solid #3a6040;
    color: #90d898;
    border-radius: 6px;
    font-family: 'Courier New', monospace;
    font-size: 0.85rem;
    width: 100%;
    transition: all 0.15s;
}
.stButton > button:hover {
    background: #234030;
    border-color: #60a870;
    color: #b0f0b8;
}
div[data-testid="column"] .stButton > button { font-size: 0.82rem; }
.stSelectbox > div, .stNumberInput > div { border-color: #2a4a30 !important; }
label { color: #7aaa80 !important; font-size: 0.8rem !important; }
.stDataFrame { background: #0d1f12; }
/* hide streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1.2rem; padding-bottom: 1rem; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SESSION STATE  — persist objects across reruns
# ══════════════════════════════════════════════════════════════════════════════
def init_state():
    if "obs" not in st.session_state:
        st.session_state.obs   = Observer(buyin_chips=400)
        st.session_state.gstate = GameState(observer=st.session_state.obs)
        st.session_state.eng   = PokerEngine(
            observer=st.session_state.obs,
            game_state=st.session_state.gstate,
        )
        st.session_state.log   = []          # action log entries
        st.session_state.hero  = ""
        st.session_state.villain = ""

init_state()
obs    = st.session_state.obs
gstate = st.session_state.gstate
eng    = st.session_state.eng

def append_log(msg: str):
    st.session_state.log.insert(0, msg)
    if len(st.session_state.log) > 60:
        st.session_state.log = st.session_state.log[:60]


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════
TILT_COLOURS = {"None": "#4a8a50", "Moderate": "#cc8822", "High": "#cc2222"}

def tilt_icon(level):
    return {"None": "✓", "Moderate": "⚠", "High": "🔥"}.get(level, "—")

def ev_class(text: str) -> str:
    t = text.lower()
    if "strong +ev" in t or "likely +ev" in t:
        return "ev-positive"
    if "marginal" in t:
        return "ev-neutral"
    return "ev-negative"

def render_insight(text, level="normal"):
    css = {"normal": "insight-row", "warn": "insight-row-warn", "danger": "insight-row-danger"}.get(level, "insight-row")
    st.markdown(f'<div class="{css}">• {text}</div>', unsafe_allow_html=True)

def badge(text, colour="green"):
    css = {"green": "profile-badge", "red": "profile-badge-red", "gold": "profile-badge-gold"}.get(colour, "profile-badge")
    st.markdown(f'<span class="{css}">{text}</span>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## ♠ Poker DST")
    st.markdown('<div class="section-title">Session Setup</div>', unsafe_allow_html=True)

    # ── Add player ──────────────────────────────────────────────────────────
    with st.expander("➕ Add Player", expanded=True):
        new_name  = st.text_input("Name", key="new_name", placeholder="e.g. Wayne")
        new_stack = st.number_input("Starting Stack", min_value=0, value=400, step=100, key="new_stack")
        if st.button("Add Player", key="btn_add"):
            name = new_name.strip()
            if name and name not in obs.all_players():
                obs.add_player(name, int(new_stack))
                append_log(f"➕ {name} joined (stack: {int(new_stack)})")
                st.rerun()
            elif name in obs.all_players():
                st.warning(f"{name} already registered.")
            else:
                st.warning("Enter a name.")

    # ── Hero & Villain selectors ─────────────────────────────────────────────
    players = obs.all_players()
    st.markdown('<div class="section-title">Current Hand</div>', unsafe_allow_html=True)

    hero_sel = st.selectbox("Hero (You)", options=["—"] + players, key="hero_sel")
    villain_sel = st.selectbox("Villain (Analyse)", options=["—"] + players, key="villain_sel")

    if hero_sel != "—":
        st.session_state.hero = hero_sel
        gstate.hand.hero = hero_sel
    if villain_sel != "—":
        st.session_state.villain = villain_sel
        gstate.hand.villain = villain_sel

    street_sel = st.selectbox("Street", ["preflop", "flop", "turn", "river"], key="street_sel")
    gstate.hand.street = street_sel

    pot_val = st.number_input("Pot (chips)", min_value=0, value=int(gstate.hand.pot), step=10, key="pot_val")
    gstate.set_pot(int(pot_val))

    st.divider()

    # ── Rebuy ────────────────────────────────────────────────────────────────
    st.markdown('<div class="section-title">Rebuys (£2 = 400 chips)</div>', unsafe_allow_html=True)
    rebuy_player = st.selectbox("Player", options=["—"] + players, key="rebuy_player")
    if st.button("💸 Record Rebuy", key="btn_rebuy"):
        if rebuy_player != "—":
            obs.record_rebuy(rebuy_player)
            append_log(f"💸 {rebuy_player} rebought (+400 chips)")
            st.rerun()

    st.divider()

    # ── Manual stack correction ──────────────────────────────────────────────
    with st.expander("🔧 Correct Stack"):
        sc_player = st.selectbox("Player", options=["—"] + players, key="sc_player")
        sc_chips  = st.number_input("New Stack", min_value=0, value=400, step=50, key="sc_chips")
        if st.button("Set Stack", key="btn_sc"):
            if sc_player != "—":
                obs.set_stack(sc_player, int(sc_chips))
                append_log(f"🔧 {sc_player} stack set to {int(sc_chips)}")
                st.rerun()

    # ── Award pot ────────────────────────────────────────────────────────────
    with st.expander("🏆 Award Pot"):
        aw_player = st.selectbox("Winner", options=["—"] + players, key="aw_player")
        aw_chips  = st.number_input("Chips", min_value=0, value=int(gstate.hand.pot), step=10, key="aw_chips")
        if st.button("Award", key="btn_award"):
            if aw_player != "—":
                obs.award_pot(aw_player, int(aw_chips))
                append_log(f"🏆 {aw_player} won {int(aw_chips)} chips")
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# MAIN LAYOUT  — three columns
# ══════════════════════════════════════════════════════════════════════════════
col_action, col_advice, col_dash = st.columns([1.1, 2.2, 1.7], gap="medium")


# ══════════════════════════════════════════════════════════════════════════════
# LEFT: ACTION LOG
# ══════════════════════════════════════════════════════════════════════════════
with col_action:
    st.markdown('<div class="section-title">Action Logger</div>', unsafe_allow_html=True)

    players = obs.all_players()
    if not players:
        st.info("Add players in the sidebar to begin.")
    else:
        # ── Target player for action ─────────────────────────────────────────
        act_player = st.selectbox("Player acting", options=players, key="act_player")
        act_size   = st.number_input("Chip amount", min_value=0, value=0, step=10, key="act_size")

        # ── Action buttons 2×2 ───────────────────────────────────────────────
        st.markdown("")
        r1c1, r1c2 = st.columns(2)
        r2c1, r2c2 = st.columns(2)
        r3c1, r3c2 = st.columns(2)

        def log_action(player, action, size=0):
            pot = gstate.hand.pot
            street = gstate.hand.street
            obs.update_game(player, action, size=size, pot=pot, street=street)
            gstate.record_action(player, action, int(size))
            size_str = f" {int(size)}" if size > 0 else ""
            append_log(f"[{street[:2].upper()}] {player}: {action}{size_str}  (pot {pot})")

        with r1c1:
            if st.button("📈 Bet", key="btn_bet"):
                log_action(act_player, "Bet", act_size)
                st.rerun()
        with r1c2:
            if st.button("🔺 Raise", key="btn_raise"):
                log_action(act_player, "Raise", act_size)
                st.rerun()
        with r2c1:
            if st.button("📞 Call", key="btn_call"):
                log_action(act_player, "Call", act_size)
                st.rerun()
        with r2c2:
            if st.button("🏳 Fold", key="btn_fold"):
                log_action(act_player, "Fold")
                st.rerun()
        with r3c1:
            if st.button("✋ Check", key="btn_check"):
                log_action(act_player, "Check")
                st.rerun()
        with r3c2:
            if st.button("🔵 Limp", key="btn_limp"):
                log_action(act_player, "Limp", act_size)
                st.rerun()

        st.divider()

        # ── Action log ───────────────────────────────────────────────────────
        st.markdown('<div class="section-title">Recent Actions</div>', unsafe_allow_html=True)
        if st.session_state.log:
            log_html = "".join(
                f'<div class="log-entry">{e}</div>'
                for e in st.session_state.log[:20]
            )
            st.markdown(log_html, unsafe_allow_html=True)
        else:
            st.markdown('<div class="log-entry">No actions yet.</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# CENTRE: ADVICE PANEL
# ══════════════════════════════════════════════════════════════════════════════
with col_advice:
    villain = st.session_state.villain
    hero    = st.session_state.hero

    st.markdown('<div class="section-title">Decision Support</div>', unsafe_allow_html=True)

    if not villain or villain == "—" or villain not in obs.all_players():
        st.markdown("""
        <div class="card" style="text-align:center; padding: 40px;">
            <div style="font-size:2.5rem; margin-bottom:12px;">♠</div>
            <div style="color:#4a8a50; font-size:0.9rem;">
                Select a <strong>Villain</strong> in the sidebar<br>to see live analysis.
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        stats   = obs.get_stats(villain)
        profile = OpponentClassifier.classify(stats)
        tilt    = TiltDetector.check_tilt(stats)

        # ── Call amount + hand strength for EV calc ──────────────────────────
        ev_cols = st.columns([1, 1])
        with ev_cols[0]:
            call_amount = st.number_input("Call amount (for EV)", min_value=0, value=0, step=10, key="call_amt")
        with ev_cols[1]:
            hand_strength = st.selectbox(
                "Hand strength",
                ["medium", "strong", "monster", "weak", "draw"],
                key="hand_str",
            )

        analysis = eng.analyse_villain(villain, call_amount=call_amount, hand_strength=hand_strength)

        # ── TILT BANNER ──────────────────────────────────────────────────────
        tilt_level = tilt.get("tilt_level", "None")
        if tilt_level == "High":
            st.markdown(f"""
            <div class="tilt-banner">
                🔥 <strong>TILT ALERT — HIGH</strong><br>
                {"<br>".join(tilt.get("tilt_reasons", []))}
            </div>""", unsafe_allow_html=True)
        elif tilt_level == "Moderate":
            st.markdown(f"""
            <div class="tilt-banner-mod">
                ⚠ <strong>TILT WARNING — MODERATE</strong><br>
                {"<br>".join(tilt.get("tilt_reasons", []))}
            </div>""", unsafe_allow_html=True)

        # ── PROFILE HEADER ───────────────────────────────────────────────────
        st.markdown(f'<div class="panel-title">🎯 {villain}</div>', unsafe_allow_html=True)

        label       = profile.get("label", "Unknown")
        bluff_t     = profile.get("bluff_tendency", "—")
        confidence  = profile.get("confidence", "low")
        dom_size    = profile.get("dominant_bet_size", "—")

        badge_colour = "red" if "Aggressive" in label else "gold" if "Loose" in label else "green"
        st.markdown(
            f'<span class="profile-badge-gold">{label}</span>'
            f'<span class="profile-badge">Bluff: {bluff_t}</span>'
            f'<span class="profile-badge">Sizing: {dom_size}</span>'
            f'<span class="profile-badge">Confidence: {confidence}</span>',
            unsafe_allow_html=True
        )

        # ── STAT MINI-DASHBOARD ───────────────────────────────────────────────
        st.markdown("")
        mc1, mc2, mc3, mc4, mc5 = st.columns(5)
        def mini_stat(col, value, label):
            col.markdown(f'<div class="stat-big">{value}</div><div class="stat-label">{label}</div>', unsafe_allow_html=True)

        mini_stat(mc1, f"{stats['vpip']}%",             "VPIP")
        mini_stat(mc2, f"{stats['pfr']}%",              "PFR")
        mini_stat(mc3, f"{stats['aggression_factor']}x", "Agg Factor")
        mini_stat(mc4, f"{stats['fold_to_bet_pct']}%",  "Fold/Bet")
        mini_stat(mc5, f"{stats['call_frequency_pct']}%","Call Freq")

        st.markdown("<br>", unsafe_allow_html=True)

        # ── INSIGHTS ─────────────────────────────────────────────────────────
        left_i, right_i = st.columns(2)

        with left_i:
            st.markdown('<div class="section-title">Bluff Assessment</div>', unsafe_allow_html=True)
            for g in analysis.get("bluff_guidance", []):
                render_insight(g, "normal")

            st.markdown('<div class="section-title" style="margin-top:12px">Value Betting</div>', unsafe_allow_html=True)
            for g in analysis.get("betting_guidance", []):
                render_insight(g, "warn")

            st.markdown('<div class="section-title" style="margin-top:12px">Sizing</div>', unsafe_allow_html=True)
            for g in analysis.get("sizing_guidance", []):
                render_insight(g, "normal")

        with right_i:
            st.markdown('<div class="section-title">Range Insights</div>', unsafe_allow_html=True)
            for g in analysis.get("overbet_insight", []):
                render_insight(g, "warn")

            if tilt.get("tilt_mode"):
                st.markdown('<div class="section-title" style="margin-top:12px">Tilt Notes</div>', unsafe_allow_html=True)
                for note in analysis.get("tilt", {}).get("notes", []):
                    render_insight(note, "danger")

            spr_ctx = analysis.get("spr_context", "")
            if spr_ctx:
                st.markdown('<div class="section-title" style="margin-top:12px">Stack Context</div>', unsafe_allow_html=True)
                render_insight(spr_ctx, "normal")

        # ── POT ODDS + EV ─────────────────────────────────────────────────────
        pot_odds = analysis.get("pot_odds", {})
        equity   = analysis.get("estimated_equity", {})
        ev_note  = analysis.get("ev_assessment", "")

        if isinstance(pot_odds, dict) and pot_odds:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown('<div class="section-title">Pot Odds & EV Analysis</div>', unsafe_allow_html=True)
            ev_c1, ev_c2, ev_c3 = st.columns(3)
            with ev_c1:
                mini_stat(ev_c1, f"{pot_odds.get('required_equity_pct', 0)}%", "Required Equity")
            with ev_c2:
                eq_label = equity.get("estimated_equity_label", "—") if isinstance(equity, dict) else "—"
                mini_stat(ev_c2, eq_label, "Est. Equity vs Range")
            with ev_c3:
                margin_lo = (equity.get("estimated_equity_lo", 0) if isinstance(equity, dict) else 0) - pot_odds.get("required_equity_pct", 0)
                margin_str = f"+{margin_lo:.0f}%" if margin_lo > 0 else f"{margin_lo:.0f}%"
                mini_stat(ev_c3, margin_str, "Equity Margin")

            ev_css = ev_class(ev_note)
            st.markdown(f'<div class="{ev_css}" style="margin-top:10px">{ev_note}</div>', unsafe_allow_html=True)
            st.markdown(f'<div style="font-size:0.72rem; color:#4a6a4a; margin-top:4px">{pot_odds.get("implied_odds_note","")}</div>', unsafe_allow_html=True)

        # ── BET SIZING BREAKDOWN ──────────────────────────────────────────────
        sizing = stats.get("bet_sizing", {})
        if stats.get("_total_bets_sized", 0) > 0:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown('<div class="section-title">Bet Sizing Breakdown</div>', unsafe_allow_html=True)
            sz_df = pd.DataFrame({
                "Size": ["Small (≤33%)", "Medium (34–66%)", "Large (67–99%)", "Overbet (≥100%)"],
                "Frequency": [
                    sizing.get("small", 0),
                    sizing.get("medium", 0),
                    sizing.get("large", 0),
                    sizing.get("overbet", 0),
                ]
            })
            st.bar_chart(sz_df.set_index("Size"), height=140, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# RIGHT: PLAYER DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
with col_dash:
    st.markdown('<div class="section-title">Player Dashboard</div>', unsafe_allow_html=True)

    players = obs.all_players()
    if not players:
        st.info("No players yet.")
    else:
        summaries = eng.session_summary()

        # ── Per-player cards ──────────────────────────────────────────────────
        for p in summaries:
            tilt_lvl = p.get("tilt", "None")
            is_villain = (p["player"] == st.session_state.villain)
            card_class = "card-red" if tilt_lvl == "High" else "card-gold" if tilt_lvl == "Moderate" else "card"

            # Determine archetype colour hint
            label_style = "color:#e07070" if "Aggressive" in p["label"] else "color:#d4b96a" if "Loose" in p["label"] else "color:#80d890"
            villain_marker = " 🎯" if is_villain else ""
            tilt_marker = f" {tilt_icon(tilt_lvl)} {tilt_lvl}" if tilt_lvl != "None" else ""

            st.markdown(f"""
            <div class="{card_class}">
                <div style="display:flex; justify-content:space-between; align-items:top">
                    <div style="font-weight:bold; color:#e8e0d0; font-size:0.95rem">{p['player']}{villain_marker}</div>
                    <div style="font-size:0.72rem; color:#{'cc2222' if tilt_lvl=='High' else 'cc8822' if tilt_lvl=='Moderate' else '4a8a50'}">{tilt_marker}</div>
                </div>
                <div style="{label_style}; font-size:0.78rem; margin:3px 0 8px 0">{p['label']} · {p['bluff_t']}</div>
                <div style="display:grid; grid-template-columns: 1fr 1fr 1fr; gap:4px; text-align:center">
                    <div>
                        <div style="font-size:1.1rem; font-weight:bold; color:#d4b96a">{p['vpip']}%</div>
                        <div style="font-size:0.6rem; color:#4a8a50; letter-spacing:0.1em">VPIP</div>
                    </div>
                    <div>
                        <div style="font-size:1.1rem; font-weight:bold; color:#d4b96a">{p['af']}x</div>
                        <div style="font-size:0.6rem; color:#4a8a50; letter-spacing:0.1em">AGG F.</div>
                    </div>
                    <div>
                        <div style="font-size:1.1rem; font-weight:bold; color:#d4b96a">{p['ftb']}%</div>
                        <div style="font-size:0.6rem; color:#4a8a50; letter-spacing:0.1em">FOLD/BET</div>
                    </div>
                </div>
                <div style="margin-top:8px; display:flex; justify-content:space-between; font-size:0.72rem; color:#5a8a60">
                    <span>Stack: <strong style="color:#90d898">{p['stack']}</strong></span>
                    <span>PFR: <strong style="color:#90d898">{p['pfr']}%</strong></span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # ── Full stats table ─────────────────────────────────────────────────
        with st.expander("📊 Full Stats Table"):
            rows = []
            for p_name in obs.all_players():
                s = obs.get_stats(p_name)
                rows.append({
                    "Player":   p_name,
                    "Hands":    s["hands_seen"],
                    "VPIP%":    s["vpip"],
                    "PFR%":     s["pfr"],
                    "FtB%":     s["fold_to_bet_pct"],
                    "Call%":    s["call_frequency_pct"],
                    "AF":       s["aggression_factor"],
                    "Stack":    s["stack"],
                    "Rebuys":   s["buyins_lost"],
                })
            df = pd.DataFrame(rows).set_index("Player")
            st.dataframe(
                df.style.background_gradient(subset=["VPIP%"], cmap="RdYlGn_r")
                        .background_gradient(subset=["AF"], cmap="RdYlGn_r")
                        .background_gradient(subset=["FtB%"], cmap="RdYlGn"),
                use_container_width=True,
            )
