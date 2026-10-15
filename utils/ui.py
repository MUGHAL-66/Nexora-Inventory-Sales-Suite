"""Shared application theme and small Streamlit presentation components."""

from __future__ import annotations

from html import escape

import streamlit as st


def render_page_header(section: str, title: str, subtitle: str) -> None:
    """Render a consistent breadcrumb, page title, and supporting description."""
    st.markdown(
        f'<div class="nx-breadcrumb"><span class="nx-breadcrumb-root">Nexora</span>'
        f'<span>/</span>{escape(section)}</div>',
        unsafe_allow_html=True,
    )
    st.title(title)
    st.markdown(
        f'<p class="nx-page-subtitle">{escape(subtitle)}</p>',
        unsafe_allow_html=True,
    )


def render_section_heading(title: str, description: str | None = None) -> None:
    """Render a compact heading for a page's table or action area."""
    description_markup = (
        f'<p class="nx-section-description">{escape(description)}</p>'
        if description
        else ""
    )
    st.markdown(
        f'<div class="nx-section-heading"><h2>{escape(title)}</h2>'
        f"{description_markup}</div>",
        unsafe_allow_html=True,
    )


def apply_theme() -> None:
    """Apply a consistent, light-only visual system across the application."""
    st.markdown(
        """
        <style>
        :root {
            color-scheme: light;
            --nx-bg: #F8F5F6;
            --nx-surface: #FFFFFF;
            --nx-sidebar: #280D18;
            --nx-sidebar-deep: #451326;
            --nx-primary: #641B35;
            --nx-primary-dark: #57162D;
            --nx-primary-hover: #842B4C;
            --nx-rose-gold: #C99A83;
            --nx-blush: #E8CFD7;
            --nx-ink: #29212A;
            --nx-muted: #786C75;
            --nx-border: #E8DEE3;
            --nx-success: #2F6D58;
            --nx-warning: #98641D;
            --nx-danger: #A63A4B;
            --nx-shadow: 0 9px 28px rgba(54, 24, 39, .065);
        }
        html, body, [data-testid="stAppViewContainer"] {
            background: var(--nx-bg);
            color: var(--nx-ink);
            font-family: Inter, "Segoe UI", Arial, sans-serif;
        }
        [data-testid="stHeader"] {
            background: rgba(248, 245, 246, .94);
            border-bottom: 1px solid rgba(232, 222, 227, .75);
        }
        [data-testid="stToolbar"] { right: 1rem; }
        [data-testid="stMainBlockContainer"] {
            max-width: 1480px;
            padding: 2rem 2.25rem 3rem;
            min-width: 0;
        }
        [data-testid="stAppViewContainer"], [data-testid="stMain"], [data-testid="stMainBlockContainer"] {
            min-width: 0;
            max-width: 100%;
        }
        h1, h2, h3, h4 {
            color: var(--nx-ink) !important;
            letter-spacing: -.035em !important;
        }
        h1 {
            font-size: 30px !important;
            line-height: 1.2 !important;
            font-weight: 710 !important;
            margin: 0 0 .25rem !important;
        }
        h2 { font-size: 23px !important; font-weight: 680 !important; }
        h3 { font-size: 18px !important; font-weight: 660 !important; }
        h4 { font-size: 15px !important; font-weight: 660 !important; }
        p, [data-testid="stCaptionContainer"] { color: var(--nx-muted); }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, var(--nx-sidebar) 0%, var(--nx-sidebar-deep) 100%);
            border-right: 0;
        }
        [data-testid="stSidebar"] > div:first-child { padding: 1.15rem .9rem 1rem; }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] { color: #FFF8FA; }
        [data-testid="stSidebar"] [data-testid="stPageLink"] a {
            display: flex;
            align-items: center;
            min-height: 2.8rem;
            padding: .58rem .82rem;
            margin: 3px 0;
            border: 1px solid transparent;
            border-radius: 10px;
            color: #F6EDEF;
            font-size: 12px;
            font-weight: 580;
            text-decoration: none;
            transition: color .18s ease, background .18s ease, border-color .18s ease, transform .18s ease, box-shadow .18s ease;
        }
        [data-testid="stSidebar"] [data-testid="stPageLink"] a:hover {
            color: #FFFFFF;
            border-color: rgba(201, 154, 131, .3);
            background: rgba(201, 154, 131, .13);
            transform: translateX(2px);
        }
        [data-testid="stSidebar"] [data-testid="stPageLink"] a:focus-visible {
            outline: 2px solid var(--nx-rose-gold);
            outline-offset: 2px;
        }
        [data-testid="stSidebar"] [data-testid="stPageLink"] a[aria-current="page"] {
            position: relative;
            color: #FFFFFF;
            border-color: rgba(232, 207, 215, .25);
            background: linear-gradient(100deg, rgba(132, 43, 76, .72), rgba(100, 27, 53, .52));
            box-shadow: 0 5px 14px rgba(17, 4, 10, .22), inset 0 1px 0 rgba(255,255,255,.055);
        }
        [data-testid="stSidebar"] [data-testid="stPageLink"] a[aria-current="page"]:before {
            content: "";
            position: absolute;
            left: -1px;
            top: 8px;
            bottom: 8px;
            width: 3px;
            border-radius: 0 3px 3px 0;
            background: var(--nx-rose-gold);
        }
        [data-testid="stSidebar"] [data-testid="stPageLink"] a [data-testid="stIconMaterial"],
        [data-testid="stSidebar"] [data-testid="stPageLink"] a svg {
            color: #D5AA98 !important;
            fill: #D5AA98 !important;
            transition: color .18s ease, fill .18s ease, transform .18s ease;
        }
        [data-testid="stSidebar"] [data-testid="stPageLink"] a:hover [data-testid="stIconMaterial"],
        [data-testid="stSidebar"] [data-testid="stPageLink"] a:hover svg,
        [data-testid="stSidebar"] [data-testid="stPageLink"] a[aria-current="page"] [data-testid="stIconMaterial"],
        [data-testid="stSidebar"] [data-testid="stPageLink"] a[aria-current="page"] svg {
            color: #F0C9B4 !important;
            fill: #F0C9B4 !important;
            transform: scale(1.04);
        }
        [data-testid="stSidebar"] [data-testid="stPageLink"] a[aria-current="page"] span {
            font-weight: 660;
        }
        [data-testid="stSidebar"] [data-testid="stButton"] button {
            justify-content: flex-start;
            text-align: left;
            min-height: 2.65rem;
            padding: .55rem .8rem;
            border-radius: 10px;
            border: 1px solid rgba(232, 207, 215, .2);
            color: #F8EEF1;
            background: rgba(255, 255, 255, .045);
            font-weight: 570;
            transition: color .18s ease, background .18s ease, border-color .18s ease, box-shadow .18s ease;
        }
        [data-testid="stSidebar"] [data-testid="stButton"] button:hover {
            border-color: rgba(201, 154, 131, .55);
            color: #FFFFFF;
            background: rgba(201, 154, 131, .14);
            box-shadow: 0 4px 12px rgba(17, 4, 10, .15);
        }
        [data-testid="stSidebar"] [data-testid="stButton"] button:focus-visible {
            outline: 2px solid var(--nx-rose-gold);
            outline-offset: 2px;
        }
        .nx-brand {
            display: flex;
            align-items: center;
            gap: 12px;
            margin: 2px 3px 11px;
            padding: 3px 5px 20px;
            border-bottom: 1px solid rgba(232, 207, 215, .18);
        }
        .nx-brand-mark, .nx-empty-mark, .nx-placeholder-mark {
            display: flex;
            align-items: center;
            justify-content: center;
            color: #FFF8FA;
            font-weight: 800;
            background: linear-gradient(145deg, #D8B09C, var(--nx-rose-gold));
            border: 1px solid rgba(255, 244, 238, .32);
            border-radius: 12px;
            box-shadow: 0 5px 15px rgba(14, 3, 8, .28);
        }
        .nx-brand-mark { width: 42px; height: 42px; font-size: 20px; }
        .nx-brand-name {
            color: #FFFFFF;
            font-size: 22px;
            line-height: 1.1;
            font-weight: 740;
            letter-spacing: -.7px;
        }
        .nx-brand-name span { color: #DAB19C; }
        .nx-brand-caption {
            margin-top: 5px;
            color: #D4BFC6;
            font-size: 8px;
            letter-spacing: 1.15px;
            font-weight: 720;
        }
        .nx-nav-group {
            margin: 19px 9px 7px;
            color: #C1A6B0;
            font-size: 9px;
            letter-spacing: 1.15px;
            font-weight: 760;
        }
        .nx-sidebar-footer {
            display: flex;
            gap: 11px;
            align-items: center;
            margin: 24px 4px 0;
            border-top: 1px solid rgba(232, 207, 215, .18);
            padding: 15px 6px 4px;
            color: #FFF8FA;
            font-size: 11px;
        }
        .nx-sidebar-footer strong, .nx-sidebar-footer span { display: block; }
        .nx-sidebar-footer span {
            margin-top: 3px;
            color: #D4BFC6;
            font-size: 10px;
        }
        .nx-status-dot {
            width: 8px;
            height: 8px;
            background: var(--nx-rose-gold);
            border-radius: 50%;
            box-shadow: 0 0 0 4px rgba(201, 154, 131, .18);
            flex: 0 0 auto;
        }

        .nx-breadcrumb { color: #8D7D86; font-size: 10px; font-weight: 620; letter-spacing: .035em; margin: 0 0 12px; }
        .nx-breadcrumb span { padding: 0 7px; color: #C8B8C0; }
        .nx-breadcrumb-root { color: var(--nx-primary); }
        .nx-page-subtitle { color: var(--nx-muted); margin: 0 0 24px; font-size: 13px; line-height: 1.55; }
        .nx-section-heading { margin: 20px 0 10px; }
        .nx-section-heading h2 {
            display: flex;
            align-items: center;
            gap: 9px;
            margin: 0 !important;
            font-size: 16px !important;
            letter-spacing: -.02em !important;
        }
        .nx-section-heading h2:before {
            content: "";
            width: 3px;
            height: 17px;
            border-radius: 2px;
            background: var(--nx-rose-gold);
        }
        .nx-section-description { margin: 5px 0 0; font-size: 11px; }
        .nx-section-spacer { height: 17px; }
        .nx-order-summary {
            margin-top: 1rem;
            padding: 13px 16px;
            border: 1px solid #E8DEE3;
            border-radius: 10px;
            background: #FBF7F9;
            color: var(--nx-primary);
            font-size: 13px;
            font-weight: 690;
            text-align: right;
        }

        .nx-kpi {
            background: var(--nx-surface);
            border: 1px solid var(--nx-border);
            border-radius: 15px;
            padding: 18px 19px 17px;
            min-height: 122px;
            box-shadow: var(--nx-shadow);
            position: relative;
            overflow: hidden;
        }
        .nx-kpi:before {
            content: "";
            position: absolute;
            left: 0;
            top: 18px;
            bottom: 18px;
            width: 3px;
            border-radius: 0 4px 4px 0;
            background: var(--nx-rose-gold);
        }
        .nx-kpi-label { color: var(--nx-muted); font-size: 11px; font-weight: 620; }
        .nx-kpi-value {
            color: var(--nx-ink);
            font-size: 25px;
            letter-spacing: -.7px;
            font-weight: 740;
            margin: 8px 0 4px;
        }
        .nx-kpi-note { color: #8E8189; font-size: 10px; }
        .nx-kpi { transition: border-color .18s ease, box-shadow .18s ease; }
        .nx-kpi:hover {
            border-color: #D8C2CC;
            box-shadow: 0 12px 30px rgba(54, 24, 39, .09);
        }

        [data-testid="stForm"] {
            padding: 1.45rem 1.5rem 1.1rem;
            background: var(--nx-surface);
            border: 1px solid var(--nx-border);
            border-radius: 15px;
            box-shadow: var(--nx-shadow);
        }
        [data-testid="stForm"] [data-testid="stFormSubmitButton"] {
            display: flex;
            justify-content: flex-end;
            margin-top: .5rem;
            padding-top: .75rem;
            border-top: 1px solid #EEF0EB;
        }
        [data-testid="stTextInput"] label,
        [data-testid="stNumberInput"] label,
        [data-testid="stSelectbox"] label,
        [data-testid="stMultiSelect"] label,
        [data-testid="stTextArea"] label,
        [data-testid="stDateInput"] label,
        [data-testid="stCheckbox"] label,
        [data-testid="stRadio"] label {
            color: #594A54;
            font-size: 12px;
            font-weight: 610;
        }
        [data-testid="stTextInput"] input,
        [data-testid="stNumberInput"] input,
        [data-testid="stTextArea"] textarea {
            background: #FFFEFF;
            border-color: #E3D8DE;
            border-radius: 9px;
            color: var(--nx-ink);
            transition: border-color .18s ease, box-shadow .18s ease, background .18s ease;
        }
        [data-testid="stTextInput"] input:hover,
        [data-testid="stNumberInput"] input:hover,
        [data-testid="stTextArea"] textarea:hover {
            border-color: #CDB5C0;
        }
        [data-testid="stTextInput"] input:focus,
        [data-testid="stNumberInput"] input:focus,
        [data-testid="stTextArea"] textarea:focus {
            border-color: var(--nx-primary);
            box-shadow: 0 0 0 3px rgba(201, 154, 131, .24);
            background: #FFFFFF;
        }
        [data-testid="stTextInputRootElement"]:focus-within,
        [data-testid="stNumberInputContainer"]:focus-within,
        [data-testid="stTextArea"] textarea:focus {
            border-color: var(--nx-primary) !important;
            box-shadow: 0 0 0 3px rgba(201, 154, 131, .24) !important;
        }
        [data-testid="stTextInput"] input:disabled,
        [data-testid="stNumberInput"] input:disabled,
        [data-testid="stTextArea"] textarea:disabled {
            color: #8E828A;
            background: #F1ECEF;
            cursor: not-allowed;
        }
        [data-testid="stSelectbox"] [data-baseweb="select"] > div,
        [data-testid="stMultiSelect"] [data-baseweb="select"] > div,
        [data-testid="stDateInput"] [data-baseweb="input"] > div {
            background: #FFFEFF;
            border-color: #E3D8DE;
            border-radius: 9px;
            transition: border-color .18s ease, box-shadow .18s ease, background .18s ease;
        }
        [data-testid="stSelectbox"] [data-baseweb="select"]:hover > div,
        [data-testid="stMultiSelect"] [data-baseweb="select"]:hover > div,
        [data-testid="stDateInput"] [data-baseweb="input"]:hover > div {
            border-color: #CDB5C0;
        }
        [data-testid="stSelectbox"] [data-baseweb="select"]:focus-within > div,
        [data-testid="stMultiSelect"] [data-baseweb="select"]:focus-within > div,
        [data-testid="stDateInput"] [data-baseweb="input"]:focus-within > div {
            border-color: var(--nx-primary);
            box-shadow: 0 0 0 3px rgba(201, 154, 131, .24);
        }
        [data-testid="stSelectbox"] [aria-disabled="true"],
        [data-testid="stMultiSelect"] [aria-disabled="true"],
        [data-testid="stDateInput"] [aria-disabled="true"] {
            color: #8E828A;
            background: #F1ECEF;
        }
        [data-testid="stCheckbox"] label, [data-testid="stRadio"] label {
            transition: color .16s ease;
        }
        [data-testid="stCheckbox"] label:hover, [data-testid="stRadio"] label:hover {
            color: var(--nx-primary);
        }
        [data-testid="stCheckbox"] input:focus-visible + div,
        [data-testid="stRadio"] input:focus-visible + div {
            outline: 2px solid var(--nx-rose-gold);
            outline-offset: 2px;
        }
        [data-testid="stTabs"] [data-baseweb="tab-list"] {
            gap: 5px;
            border-bottom: 1px solid var(--nx-border);
        }
        [data-testid="stTabs"] [data-baseweb="tab"] {
            height: 42px;
            color: #786C75;
            font-size: 12px;
            font-weight: 600;
            transition: color .16s ease, background .16s ease;
        }
        [data-testid="stTabs"] [data-baseweb="tab"]:hover { color: var(--nx-primary); }
        [data-testid="stTabs"] [data-baseweb="tab"]:focus-visible {
            outline: 2px solid var(--nx-rose-gold);
            outline-offset: 2px;
        }
        [data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] {
            color: var(--nx-primary-dark);
            border-bottom-color: var(--nx-rose-gold);
        }
        [data-testid="stTabs"] [data-baseweb="tab-panel"] { padding-top: 1rem; }
        [data-testid="stTabs"] [data-baseweb="tab-highlight"] { background: var(--nx-rose-gold); }
        [data-testid="stButton"] button,
        [data-testid="stFormSubmitButton"] button,
        [data-testid="stDownloadButton"] button {
            min-height: 2.45rem;
            padding: .48rem 1rem;
            border-radius: 9px;
            border: 1px solid #E2D6DC;
            color: #594A54;
            background: #FFFFFF;
            font-size: 12px;
            font-weight: 640;
            transition: transform .18s ease, color .18s ease, border-color .18s ease, box-shadow .18s ease, background .18s ease;
        }
        [data-testid="stButton"] button:hover,
        [data-testid="stDownloadButton"] button:hover,
        [data-testid="stFormSubmitButton"] button:hover {
            border-color: #C99A83;
            color: var(--nx-primary);
            background: #FBF6F8;
            box-shadow: 0 4px 12px rgba(54, 24, 39, .08);
            transform: translateY(-1px);
        }
        [data-testid="stFormSubmitButton"] button[kind^="primary"],
        [data-testid="stButton"] button[kind^="primary"],
        [data-testid="stDownloadButton"] button[kind^="primary"] {
            color: #FFFFFF;
            border-color: var(--nx-primary-dark);
            background: var(--nx-primary-dark);
            box-shadow: 0 4px 11px rgba(87, 22, 45, .2);
        }
        [data-testid="stFormSubmitButton"] button[kind^="primary"]:hover,
        [data-testid="stButton"] button[kind^="primary"]:hover,
        [data-testid="stDownloadButton"] button[kind^="primary"]:hover {
            color: #FFFFFF;
            border-color: var(--nx-primary-hover);
            background: var(--nx-primary-hover);
            transform: translateY(-1px);
        }
        [data-testid="stButton"] button:focus-visible,
        [data-testid="stFormSubmitButton"] button:focus-visible,
        [data-testid="stDownloadButton"] button:focus-visible {
            outline: 3px solid rgba(201, 154, 131, .55);
            outline-offset: 2px;
        }
        [data-testid="stButton"] button:active,
        [data-testid="stFormSubmitButton"] button:active,
        [data-testid="stDownloadButton"] button:active {
            transform: translateY(0) scale(.99);
        }
        [data-testid="stButton"] button:disabled,
        [data-testid="stFormSubmitButton"] button:disabled,
        [data-testid="stDownloadButton"] button:disabled {
            color: #9A8E95;
            border-color: #E8E1E5;
            background: #F2EEF0;
            box-shadow: none;
            cursor: not-allowed;
            transform: none;
        }
        [data-testid="stDataFrame"],
        [data-testid="stTable"] {
            min-width: 0;
            max-width: 100%;
            overflow: auto;
            -webkit-overflow-scrolling: touch;
            overscroll-behavior-x: contain;
            background: var(--nx-surface);
            border: 1px solid var(--nx-border);
            border-radius: 13px;
            box-shadow: 0 4px 14px rgba(54, 24, 39, .04);
        }
        [data-testid="stDataFrame"] [role="columnheader"],
        [data-testid="stTable"] thead th {
            color: #594A54;
            font-size: 11px;
            font-weight: 680;
        }
        [data-testid="stTable"] tbody tr {
            border-bottom: 1px solid #F0E9ED;
            transition: background .16s ease;
        }
        [data-testid="stTable"] tbody tr:hover { background: #FBF6F8; }
        [data-testid="stTable"] td {
            padding: .65rem .75rem;
            color: #51454E;
            font-size: 11px;
        }
        [data-testid="stPlotlyChart"] {
            min-width: 0;
            max-width: 100%;
            padding: 9px 10px 4px;
            background: var(--nx-surface);
            border: 1px solid var(--nx-border);
            border-radius: 14px;
            box-shadow: var(--nx-shadow);
        }
        [data-testid="stAlert"] {
            border-radius: 10px;
            border: 1px solid #E8DEE3;
        }
        [data-testid="stAlert"][kind="success"] { border-color: #C7DED4; }
        [data-testid="stAlert"][kind="warning"] { border-color: #EAD8B5; }
        [data-testid="stAlert"][kind="error"] { border-color: #E8C7CD; }
        .nx-setup-card, .nx-empty-state, .nx-placeholder, .nx-chart-empty {
            background: var(--nx-surface);
            border: 1px solid var(--nx-border);
            border-radius: 15px;
            box-shadow: var(--nx-shadow);
        }
        .nx-setup-card {
            margin: 17px 0;
            padding: 21px 23px;
            border-left: 3px solid var(--nx-rose-gold);
        }
        .nx-setup-kicker {
            color: var(--nx-primary);
            font-size: 9px;
            font-weight: 760;
            letter-spacing: 1.1px;
        }
        .nx-setup-card h3 { margin: 8px 0 5px; font-size: 17px; }
        .nx-setup-card p, .nx-empty-state p, .nx-placeholder p {
            color: var(--nx-muted);
            font-size: 12px;
            line-height: 1.65;
            margin: 0;
        }
        .nx-empty-state { margin-top: 19px; padding: 27px; text-align: center; }
        .nx-empty-mark, .nx-placeholder-mark {
            width: 34px;
            height: 34px;
            margin: 0 auto 12px;
            font-size: 16px;
            border-radius: 10px;
        }
        .nx-empty-state h3, .nx-placeholder h3 { margin: 0 0 5px; font-size: 15px; }
        .nx-placeholder { margin-top: 24px; padding: 42px 28px; text-align: center; }
        .nx-placeholder p { max-width: 510px; margin: 0 auto; }
        .st-key-login_brand {
            position: relative;
            isolation: isolate;
            display: flex;
            flex-direction: column;
            justify-content: center;
            min-height: 520px;
            overflow: hidden;
            padding: 3rem;
            border: 1px solid rgba(255, 255, 255, .1);
            border-radius: 22px;
            background:
                radial-gradient(ellipse at 90% 6%, rgba(201,154,131,.18), transparent 35%),
                linear-gradient(145deg, #280D18 0%, #451326 58%, #57162D 100%);
            box-shadow: 0 18px 44px rgba(54, 18, 35, .18);
        }
        .st-key-login_brand:before,
        .st-key-login_brand:after {
            content: "";
            position: absolute;
            z-index: -1;
            border: 1px solid rgba(232, 207, 215, .12);
            border-radius: 50%;
            pointer-events: none;
        }
        .st-key-login_brand:before {
            width: 310px;
            height: 310px;
            right: -142px;
            bottom: -104px;
            box-shadow: 0 0 0 28px rgba(232,207,215,.025), 0 0 0 58px rgba(232,207,215,.02);
        }
        .st-key-login_brand:after {
            width: 130px;
            height: 130px;
            left: -74px;
            top: 52%;
            box-shadow: 0 0 0 18px rgba(232,207,215,.025);
        }
        .st-key-login_brand [data-testid="stMarkdownContainer"] { position: relative; z-index: 1; }
        .st-key-login_brand h1 {
            max-width: 430px;
            margin: 1.1rem 0 .9rem !important;
            color: #FFF9FB !important;
            font-size: clamp(32px, 3vw, 45px) !important;
            line-height: 1.08 !important;
            letter-spacing: -.045em !important;
        }
        .nx-login-brand { display: flex; align-items: center; gap: 13px; margin: 0 0 2.5rem; }
        .nx-login-brand .nx-brand-name { color: #FFFFFF; font-size: 24px; }
        .nx-login-brand .nx-brand-caption { color: #DCC8D0; }
        .nx-login-brand .nx-brand-mark {
            width: 47px;
            height: 47px;
            color: #451326;
            font-size: 22px;
            border-radius: 14px;
            box-shadow: 0 7px 19px rgba(14,3,8,.28);
        }
        .nx-login-overline {
            color: #DAB6A5;
            font-size: 10px;
            font-weight: 720;
            letter-spacing: 1.55px;
            text-transform: uppercase;
        }
        .nx-login-copy {
            max-width: 390px;
            color: #E4D4DA;
            font-size: 14px;
            line-height: 1.8;
        }
        .nx-login-brand-footer {
            margin-top: 3.2rem;
            padding-top: 1rem;
            border-top: 1px solid rgba(232,207,215,.2);
            color: #CBB4BE;
            font-size: 10px;
            letter-spacing: .045em;
        }
        .st-key-login_panel {
            padding: 2.3rem 2.25rem 2rem;
            border: 1px solid rgba(232, 222, 227, .95);
            border-radius: 22px;
            background: #FFFFFF;
            box-shadow: 0 18px 48px rgba(54, 24, 39, .085);
        }
        .st-key-login_panel h1 {
            margin-top: .2rem !important;
            color: var(--nx-ink) !important;
            font-size: 30px !important;
        }
        .st-key-login_panel .nx-page-subtitle { margin-bottom: 1.4rem; }
        .st-key-login_panel [data-testid="stForm"] {
            padding: 1.25rem;
            border-color: #F0E8EC;
            border-radius: 14px;
            box-shadow: none;
        }
        .st-key-login_panel [data-testid="stForm"] [data-testid="stFormSubmitButton"] {
            display: block;
            margin-top: 1.05rem;
            padding-top: 0;
            border-top: 0;
        }
        .st-key-login_panel [data-testid="stFormSubmitButton"] button {
            min-height: 2.8rem;
            font-size: 13px;
            letter-spacing: .01em;
        }
        .nx-login-note {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-top: 17px;
            padding-top: 13px;
            border-top: 1px solid var(--nx-border);
            color: var(--nx-muted);
            font-size: 10px;
        }
        .nx-login-note:before {
            content: "";
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: var(--nx-rose-gold);
            box-shadow: 0 0 0 3px rgba(201, 154, 131, .2);
        }
        .nx-chart-empty {
            display: flex;
            flex-direction: column;
            justify-content: center;
            gap: 6px;
            min-height: 280px;
            padding: 25px;
            text-align: center;
            color: var(--nx-ink);
        }
        .nx-chart-empty span { color: var(--nx-muted); font-size: 12px; }
        @media (max-width: 850px) {
            [data-testid="stMainBlockContainer"] { padding: 1.35rem 1rem 2rem; }
            h1 { font-size: 25px !important; }
            .nx-kpi { min-height: 108px; padding: 15px; }
            .nx-kpi-value { font-size: 21px; }
            [data-testid="stForm"] { padding: 1rem; }
            .st-key-login_panel { padding: 1.35rem; }
            .st-key-login_brand { min-height: 450px; padding: 2rem; }
            [data-testid="stHorizontalBlock"] {
                flex-wrap: wrap !important;
                align-items: stretch;
                row-gap: .8rem;
                column-gap: 1rem;
            }
            [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
                flex: 0 0 calc(50% - .5rem) !important;
                width: calc(50% - .5rem) !important;
                min-width: 0 !important;
            }
            [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:only-child {
                flex-basis: 100% !important;
                width: 100% !important;
            }
            [data-testid="stTabs"] [data-baseweb="tab-list"] {
                max-width: 100%;
                overflow-x: auto;
                overscroll-behavior-x: contain;
                scrollbar-width: thin;
            }
            [data-testid="stTabs"] [data-baseweb="tab"] { flex: 0 0 auto; }
        }
        @media (max-width: 600px) {
            [data-testid="stMainBlockContainer"] { padding-left: .75rem; padding-right: .75rem; }
            .nx-brand { padding-bottom: 16px; }
            .nx-chart-empty { min-height: 210px; }
            .st-key-login_brand { min-height: 260px; padding: 1.5rem; }
            .st-key-login_brand h1 { font-size: 31px !important; }
            .nx-login-brand { margin-bottom: 1.4rem; }
            .nx-login-brand-footer { margin-top: 1.5rem; }
            .st-key-login_panel { padding: 1.25rem; }
            [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
                flex-basis: 100% !important;
                width: 100% !important;
            }
            .st-key-login_layout [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
                flex: 1 1 100% !important;
                width: 100% !important;
            }
            .st-key-dashboard_metrics [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
                flex: 0 0 calc(50% - .5rem) !important;
                width: calc(50% - .5rem) !important;
            }
            .nx-order-summary {
                text-align: left;
                line-height: 1.8;
                overflow-wrap: anywhere;
            }
            [data-testid="stDataFrame"], [data-testid="stTable"] { font-size: 10px; }
        }
        @media (prefers-reduced-motion: reduce) {
            *, *:before, *:after {
                scroll-behavior: auto !important;
                transition-duration: .01ms !important;
                animation-duration: .01ms !important;
                animation-iteration-count: 1 !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_kpi_card(label: str, value: str, note: str) -> None:
    """Render a consistently styled, escaped KPI card."""
    st.markdown(
        f'<div class="nx-kpi"><div class="nx-kpi-label">{escape(label)}</div>'
        f'<div class="nx-kpi-value">{escape(value)}</div>'
        f'<div class="nx-kpi-note">{escape(note)}</div></div>',
        unsafe_allow_html=True,
    )
