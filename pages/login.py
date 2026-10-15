"""Sign-in page for Nexora."""

from __future__ import annotations

from typing import Any

import streamlit as st

from services.auth_service import authenticate


def render_login(connection: Any) -> None:
    """Render a functional sign-in form without retaining the submitted password."""
    with st.container(key="login_layout"):
        brand_panel, sign_in_panel = st.columns(
            [1.05, 0.95],
            gap="large",
            vertical_alignment="center",
        )
        with brand_panel:
            with st.container(key="login_brand"):
                st.markdown(
                    '<div class="nx-login-brand"><div class="nx-brand-mark">N</div>'
                    '<div><div class="nx-brand-name">nexora<span>.</span></div>'
                    '<div class="nx-brand-caption">INVENTORY &amp; SALES SUITE</div></div></div>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    '<div class="nx-login-overline">Inventory &amp; sales, in sync</div>',
                    unsafe_allow_html=True,
                )
                st.title("Control Your Business. Confidently.")
                st.markdown(
                    '<p class="nx-login-copy">A clear view of your catalog, stock, customers, '
                    'and sales in one focused workspace.</p>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    '<div class="nx-login-brand-footer">INVENTORY MANAGEMENT&nbsp;&nbsp;·&nbsp;&nbsp;SALES OPERATIONS</div>',
                    unsafe_allow_html=True,
                )

        with sign_in_panel:
            with st.container(key="login_panel"):
                st.markdown('<div class="nx-login-overline">Your workspace</div>', unsafe_allow_html=True)
                st.title("Welcome Back")
                st.markdown(
                    '<p class="nx-page-subtitle">Sign in to your Nexora workspace.</p>',
                    unsafe_allow_html=True,
                )
                with st.form("login_form", clear_on_submit=True):
                    username = st.text_input("Username", autocomplete="username")
                    password = st.text_input("Password", type="password", autocomplete="current-password")
                    submitted = st.form_submit_button("Sign in", type="primary", width="stretch")
                if submitted:
                    user = authenticate(connection, username, password)
                    if user is None:
                        st.error("We could not sign you in. Check your credentials or contact an administrator.")
                    else:
                        st.session_state["authenticated_user_id"] = user["id"]
                        st.rerun()
                st.markdown(
                    '<div class="nx-login-note">Workspace access is managed by your administrator.</div>',
                    unsafe_allow_html=True,
                )
