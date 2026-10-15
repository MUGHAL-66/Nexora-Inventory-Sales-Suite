"""Administrator user management views."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from services.auth_service import create_user, deactivate_user, list_users
from services.authorization import SUPPORTED_USER_ROLES, USER_ROLE_LABELS
from utils.ui import render_page_header, render_section_heading


def render_users_page(connection: Any, user: dict[str, Any]) -> None:
    render_page_header(
        "Administration",
        "User Management",
        "Manage workspace access with role-appropriate permissions.",
    )
    users = list_users(connection, user["id"])
    render_section_heading("Workspace accounts", "Review each account's role and current access status.")
    if users:
        display = pd.DataFrame(users).rename(
            columns={
                "username": "Username",
                "email": "Email",
                "full_name": "Name",
                "role": "Role",
                "is_active": "Active",
                "created_at": "Added",
            }
        )
        display["Role"] = display["Role"].map(USER_ROLE_LABELS)
        st.dataframe(
            display[["Username", "Email", "Name", "Role", "Active", "Added"]],
            hide_index=True,
            width="stretch",
            column_config={"Added": st.column_config.DatetimeColumn("Added")},
        )
    render_section_heading("Access controls", "Create a user account or deactivate an existing account.")
    add_tab, access_tab = st.tabs(["Add user", "Deactivate access"])
    with add_tab:
        with st.form("create_user_form", clear_on_submit=True):
            fields = st.columns(2)
            username = fields[0].text_input("Username *")
            email = fields[1].text_input("Email *")
            full_name = st.text_input("Full name *")
            role = st.selectbox(
                "Role",
                options=SUPPORTED_USER_ROLES,
                format_func=USER_ROLE_LABELS.__getitem__,
            )
            fields = st.columns(2)
            password = fields[0].text_input("Temporary password *", type="password")
            confirmation = fields[1].text_input("Confirm password *", type="password")
            st.caption("Passwords must contain at least 12 characters. They are stored as bcrypt hashes.")
            submitted = st.form_submit_button("Create user", type="primary")
        if submitted:
            if password != confirmation:
                st.error("Passwords do not match.")
            else:
                try:
                    create_user(
                        connection,
                        user["id"],
                        username=username,
                        email=email,
                        full_name=full_name,
                        role=role,
                        password=password,
                    )
                    st.success("User created.")
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
    with access_tab:
        eligible = [record for record in users if record["is_active"]]
        if not eligible:
            st.info("There are no active accounts to deactivate.")
        else:
            target = st.selectbox(
                "Account",
                eligible,
                format_func=lambda record: (
                    f"{record['full_name']} · {record['username']} · "
                        f"{USER_ROLE_LABELS[record['role']]}"
                ),
            )
            if target["id"] == user["id"]:
                st.info("You cannot deactivate your own account.")
            elif st.button("Deactivate account", type="secondary"):
                try:
                    deactivate_user(connection, user["id"], target["id"])
                    st.success("Account deactivated.")
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
