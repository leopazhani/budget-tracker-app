"""
Streamlit web application for tracking monthly expenses, funds and loans.

This app reads data from the provided Excel file and displays interactive
dashboards showing spending trends, funds allocations and outstanding loans.
Users can also add new monthly data either by uploading another Excel file
or by manually entering categories and amounts via an editable table.

To run the app locally:

    pip install streamlit pandas numpy
    streamlit run app.py

For deployment instructions (e.g. Streamlit Community Cloud), refer to the
README.md file included with this project.
"""

import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime
from io import BytesIO


def parse_month_sheet(df: pd.DataFrame):
    """Parse a single month's sheet into categories, funds, loans.

    Each sheet in the workbook follows a similar pattern: categories and
    their planned/actual values appear below the 'Home' row, followed
    optionally by a 'Bangalore' section, a 'Funds' section and two loan
    sections ('Loans/Interest - Home Side' and 'Friends Side').

    Parameters
    ----------
    df : pd.DataFrame
        Raw dataframe of the sheet as read with header=None.

    Returns
    -------
    tuple of lists
        categories, funds, loans_home, loans_friends where each is a
        list of dictionaries describing the rows found in the sheet.
    """
    categories: list[dict] = []
    funds: list[dict] = []
    loans_home: list[dict] = []
    loans_friends: list[dict] = []

    # Helper to find section starting index by matching a value in column 0
    def find_row_index(col: int, keyword: str) -> int | None:
        for i in range(len(df)):
            cell = df.iat[i, col]
            if isinstance(cell, str) and cell.strip().lower() == keyword:
                return i
        return None

    # Parse main categories under 'Home'
    start = find_row_index(0, 'home')
    if start is not None:
        i = start + 1
        while i < len(df):
            name = df.iat[i, 0]
            # stop at first blank or new section header
            if pd.isna(name):
                break
            name_str = str(name).strip()
            lower_name = name_str.lower()
            if lower_name in {'bangalore', 'funds', 'salary', 'loans/interest - home side', 'friends side', 'loans/interest'}:
                break
            planned = df.iat[i, 1] if not pd.isna(df.iat[i, 1]) else None
            # actual may be numeric; ignore non-numeric strings
            actual_cell = df.iat[i, 2] if df.shape[1] > 2 else None
            actual = actual_cell if (actual_cell is not None and pd.notna(actual_cell) and not isinstance(actual_cell, str)) else None
            categories.append({
                'Category': name_str,
                'Planned': planned,
                'Actual': actual,
            })
            i += 1

    # Parse optional Bangalore section
    bang_idx = find_row_index(0, 'bangalore')
    if bang_idx is not None:
        j = bang_idx + 1
        while j < len(df):
            name = df.iat[j, 0]
            if pd.isna(name):
                break
            name_str = str(name).strip()
            lower_name = name_str.lower()
            if lower_name in {'funds', 'salary', 'loans/interest - home side', 'friends side', 'loans/interest'}:
                break
            planned = df.iat[j, 1] if not pd.isna(df.iat[j, 1]) else None
            actual_cell = df.iat[j, 2] if df.shape[1] > 2 else None
            actual = actual_cell if (actual_cell is not None and pd.notna(actual_cell) and not isinstance(actual_cell, str)) else None
            categories.append({
                'Category': f'Bangalore - {name_str}',
                'Planned': planned,
                'Actual': actual,
            })
            j += 1

    # Parse funds section. The header 'Funds' resides in column 7.
    funds_header_idx = None
    if df.shape[1] > 7:
        for i in range(len(df)):
            cell = df.iat[i, 7]
            if isinstance(cell, str) and cell.strip().lower() == 'funds':
                funds_header_idx = i
                break
        if funds_header_idx is not None:
            k = funds_header_idx + 1
            while k < len(df):
                cat = df.iat[k, 7]
                if pd.isna(cat):
                    break
                cat_str = str(cat).strip()
                lower_cat = cat_str.lower()
                # skip reserved rows
                if lower_cat in {'planned payments', 'salary'}:
                    k += 1
                    continue
                amount = df.iat[k, 8] if df.shape[1] > 8 and pd.notna(df.iat[k, 8]) else None
                funds.append({'Fund': cat_str, 'Amount': amount})
                k += 1

    # Parse loans (Home side)
    loans_header_idx = None
    if df.shape[1] > 10:
        for i in range(len(df)):
            cell = df.iat[i, 10]
            if isinstance(cell, str) and cell.strip().lower().startswith('loans/interest'):
                loans_header_idx = i
                break
        if loans_header_idx is not None:
            k = loans_header_idx + 1
            while k < len(df):
                loan_name = df.iat[k, 10]
                if pd.isna(loan_name):
                    break
                loan_str = str(loan_name).strip()
                if loan_str.lower().startswith('friends side'):
                    break
                amount = df.iat[k, 11] if df.shape[1] > 11 and pd.notna(df.iat[k, 11]) else None
                loans_home.append({'Loan': loan_str, 'Outstanding': amount})
                k += 1

    # Parse loans (Friends side)
    friends_header_idx = None
    if df.shape[1] > 10:
        for i in range(len(df)):
            cell = df.iat[i, 10]
            if isinstance(cell, str) and cell.strip().lower().startswith('friends side'):
                friends_header_idx = i
                break
        if friends_header_idx is not None:
            k = friends_header_idx + 1
            while k < len(df):
                friend_name = df.iat[k, 10]
                if pd.isna(friend_name):
                    break
                friend_str = str(friend_name).strip()
                amount = df.iat[k, 11] if df.shape[1] > 11 and pd.notna(df.iat[k, 11]) else None
                loans_friends.append({'Friend': friend_str, 'Outstanding': amount})
                k += 1

    return categories, funds, loans_home, loans_friends


@st.cache_data(show_spinner=False)
def load_workbook(file: BytesIO | str):
    """Load and parse the workbook, returning aggregated DataFrames.

    The Streamlit cache ensures that repeated calls with the same file
    contents do not re-parse the workbook unnecessarily.

    Parameters
    ----------
    file : BytesIO | str
        File-like object or path to the Excel workbook.

    Returns
    -------
    tuple of pd.DataFrame
        cat_df, funds_df, loans_home_df, loans_friends_df
    """
    xls = pd.ExcelFile(file)
    cat_rows: list[dict] = []
    funds_rows: list[dict] = []
    loans_home_rows: list[dict] = []
    loans_friends_rows: list[dict] = []
    for sheet_name in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet_name, header=None)
        categories, funds, loans_home, loans_friends = parse_month_sheet(df)
        for cat in categories:
            cat_rows.append({
                'Month': sheet_name,
                'Category': cat['Category'],
                'Planned': cat['Planned'],
                'Actual': cat['Actual'],
            })
        for f in funds:
            funds_rows.append({
                'Month': sheet_name,
                'Fund': f['Fund'],
                'Amount': f['Amount'],
            })
        for l in loans_home:
            loans_home_rows.append({
                'Month': sheet_name,
                'Loan': l['Loan'],
                'Outstanding': l['Outstanding'],
            })
        for l in loans_friends:
            loans_friends_rows.append({
                'Month': sheet_name,
                'Friend': l['Friend'],
                'Outstanding': l['Outstanding'],
            })
    cat_df = pd.DataFrame(cat_rows)
    funds_df = pd.DataFrame(funds_rows)
    loans_home_df = pd.DataFrame(loans_home_rows)
    loans_friends_df = pd.DataFrame(loans_friends_rows)
    return cat_df, funds_df, loans_home_df, loans_friends_df


def month_to_datetime(month_str: str) -> datetime:
    """Convert strings like 'July-25' to a datetime for sorting.

    The day defaults to the first of the month. Assumes the format
    '<Month name>-<YY>'.
    """
    try:
        return datetime.strptime('1-' + month_str, '%d-%b-%y')
    except ValueError:
        # Fallback if month name is abbreviated differently (e.g. Jun instead of June)
        try:
            return datetime.strptime('1-' + month_str, '%d-%b-%Y')
        except ValueError:
            return pd.NaT


def show_dashboard(cat_df: pd.DataFrame):
    st.header("📊 Monthly Expense Dashboard")
    if cat_df.empty:
        st.warning("No data available to display. Please upload or enter some data.")
        return

    # Convert Month to datetime for sorting and grouping
    df = cat_df.copy()
    df['Month_dt'] = df['Month'].apply(month_to_datetime)
    df = df.dropna(subset=['Month_dt'])
    df = df.sort_values('Month_dt')

    # Aggregate totals per month
    totals = df.groupby('Month_dt').agg({'Planned': 'sum', 'Actual': 'sum'}).reset_index()
    totals['MonthStr'] = totals['Month_dt'].dt.strftime('%b-%Y')
    totals = totals.set_index('MonthStr')[['Planned', 'Actual']]

    # Line chart for total planned vs actual
    st.subheader("Total Planned vs Actual per Month")
    st.line_chart(totals)

    # Display overspending table
    st.subheader("Overspending by Month (Actual > Planned)")
    over_df = df.dropna(subset=['Actual'])
    over_df = over_df[over_df['Actual'] > over_df['Planned']]
    if not over_df.empty:
        over_df['Difference'] = over_df['Actual'] - over_df['Planned']
        over_df_display = over_df[['Month', 'Category', 'Planned', 'Actual', 'Difference']]
        st.dataframe(over_df_display)
    else:
        st.write("No overspending detected for the available months.")

    # Top categories by spend (sum of actuals across months)
    st.subheader("Top Spending Categories (sum of Actual across months)")
    top_cats = df.groupby('Category')['Actual'].sum().sort_values(ascending=False).head(5)
    st.bar_chart(top_cats)

    # Category trend selector
    st.subheader("Trend for Selected Category")
    unique_categories = sorted(df['Category'].unique())
    selected = st.selectbox("Pick a category to view its planned vs actual trend:", unique_categories, index=0)
    cat_trend = df[df['Category'] == selected].copy()
    # Prepare chart data
    cat_trend['MonthStr'] = cat_trend['Month_dt'].dt.strftime('%b-%Y')
    cat_trend = cat_trend.set_index('MonthStr')[['Planned', 'Actual']]
    st.line_chart(cat_trend)


def show_add_data(cat_df: pd.DataFrame, funds_df: pd.DataFrame, loans_home_df: pd.DataFrame, loans_friends_df: pd.DataFrame, workbook_path: str):
    st.header("📥 Add or Import Monthly Data")
    st.write("""
    Use this page to append a new month's data to your workbook. You can either
    upload an Excel file following the same structure as existing sheets or
    manually enter data in the editable table below. After saving, the new
    data will appear on the dashboard.
    """)

    # Section: upload new Excel
    st.subheader("Upload a New Month's Sheet")
    uploaded_file = st.file_uploader("Upload an Excel file with a single sheet for the new month", type=["xlsx"])
    if uploaded_file is not None:
        try:
            # Parse and display contents
            df = pd.read_excel(uploaded_file, sheet_name=0, header=None)
            categories, funds_list, loans_home_list, loans_friends_list = parse_month_sheet(df)
            # Display summary
            st.success(f"Parsed {len(categories)} expense categories, {len(funds_list)} funds, {len(loans_home_list)} home loans and {len(loans_friends_list)} friend loans from the uploaded sheet.")
            # Append to existing data frames (in-memory only)
            new_month_name = st.text_input("Enter the month name (e.g. Aug-25) for this sheet:")
            if new_month_name:
                # Build temporary dfs
                new_cat_rows = pd.DataFrame([
                    {'Month': new_month_name, 'Category': c['Category'], 'Planned': c['Planned'], 'Actual': c['Actual']}
                    for c in categories
                ])
                new_fund_rows = pd.DataFrame([
                    {'Month': new_month_name, 'Fund': f['Fund'], 'Amount': f['Amount']}
                    for f in funds_list
                ])
                new_loans_home = pd.DataFrame([
                    {'Month': new_month_name, 'Loan': l['Loan'], 'Outstanding': l['Outstanding']}
                    for l in loans_home_list
                ])
                new_loans_friends = pd.DataFrame([
                    {'Month': new_month_name, 'Friend': l['Friend'], 'Outstanding': l['Outstanding']}
                    for l in loans_friends_list
                ])
                if st.button("Preview & Save to Session"):
                    st.write("### Preview of new categories")
                    st.dataframe(new_cat_rows)
                    # Append to session state
                    st.session_state.setdefault('new_cat_data', pd.DataFrame())
                    st.session_state['new_cat_data'] = pd.concat([st.session_state['new_cat_data'], new_cat_rows], ignore_index=True)
                    st.session_state.setdefault('new_funds_data', pd.DataFrame())
                    st.session_state['new_funds_data'] = pd.concat([st.session_state['new_funds_data'], new_fund_rows], ignore_index=True)
                    st.session_state.setdefault('new_loans_home', pd.DataFrame())
                    st.session_state['new_loans_home'] = pd.concat([st.session_state['new_loans_home'], new_loans_home], ignore_index=True)
                    st.session_state.setdefault('new_loans_friends', pd.DataFrame())
                    st.session_state['new_loans_friends'] = pd.concat([st.session_state['new_loans_friends'], new_loans_friends], ignore_index=True)
                    st.success("Data added to session. Visit the dashboard to see updated charts.")
        except Exception as e:
            st.error(f"Failed to parse uploaded file: {e}")

    st.markdown("---")
    # Section: manual entry
    st.subheader("Manually Enter a New Month's Expenses")
    st.write("Enter a new month's expenses in the table below. You can add rows and edit cells.")
    month_input = st.text_input("New Month name (e.g. Aug-25)", key='manual_month')
    # Provide an editable dataframe template
    template_df = pd.DataFrame({
        'Category': [''],
        'Planned': [0.0],
        'Actual': [0.0],
    })
    edited_df = st.data_editor(template_df, num_rows="dynamic", key='manual_editor')
    if st.button("Save Manual Data"):
        if not month_input:
            st.error("Please provide a month name before saving.")
        else:
            # filter out empty category names
            valid_rows = edited_df[edited_df['Category'].astype(str).str.strip() != '']
            if valid_rows.empty:
                st.error("No valid rows to save.")
            else:
                new_rows = valid_rows.copy()
                new_rows['Month'] = month_input
                new_rows = new_rows[['Month', 'Category', 'Planned', 'Actual']]
                st.session_state.setdefault('new_cat_data', pd.DataFrame())
                st.session_state['new_cat_data'] = pd.concat([st.session_state['new_cat_data'], new_rows], ignore_index=True)
                st.success(f"Added {len(new_rows)} new expense rows for {month_input}.")


def show_funds_loans(funds_df: pd.DataFrame, loans_home_df: pd.DataFrame, loans_friends_df: pd.DataFrame):
    st.header("💰 Funds & Loans Overview")
    if funds_df.empty and 'new_funds_data' not in st.session_state:
        st.info("No funds data available.")
    else:
        # Combine existing and new funds data
        funds = funds_df.copy()
        if 'new_funds_data' in st.session_state:
            funds = pd.concat([funds, st.session_state['new_funds_data']], ignore_index=True)
        # Convert months for plotting
        funds['Month_dt'] = funds['Month'].apply(month_to_datetime)
        funds = funds.dropna(subset=['Month_dt'])
        # Show bar chart of funds per month by category
        st.subheader("Funds Allocation by Month")
        pivot = funds.pivot_table(index=funds['Month_dt'].dt.strftime('%b-%Y'), columns='Fund', values='Amount', aggfunc='sum').fillna(0)
        st.bar_chart(pivot)

    st.markdown("---")
    # Loans section
    st.subheader("Outstanding Loans")
    # Combine existing and new loans
    loans_home = loans_home_df.copy()
    if 'new_loans_home' in st.session_state:
        loans_home = pd.concat([loans_home, st.session_state['new_loans_home']], ignore_index=True)
    loans_friends = loans_friends_df.copy()
    if 'new_loans_friends' in st.session_state:
        loans_friends = pd.concat([loans_friends, st.session_state['new_loans_friends']], ignore_index=True)

    if loans_home.empty and loans_friends.empty:
        st.info("No loan data available.")
    else:
        # Group by month and loan/friend name
        if not loans_home.empty:
            st.write("### Home Loans")
            home_pivot = loans_home.pivot_table(index='Month', columns='Loan', values='Outstanding', aggfunc='sum').fillna(0)
            st.bar_chart(home_pivot)
        if not loans_friends.empty:
            st.write("### Loans to Friends")
            friend_pivot = loans_friends.pivot_table(index='Month', columns='Friend', values='Outstanding', aggfunc='sum').fillna(0)
            st.bar_chart(friend_pivot)


def main():
    st.set_page_config(page_title="Budget Dashboard", layout="wide")
    st.title("📒 Budget & Commitment Tracker")

    # -------------------------------------------------------------------------
    # Simple authentication layer
    # -------------------------------------------------------------------------
    # Use Streamlit's secrets mechanism for credentials. On Streamlit Cloud
    # deploy, set the values in `.streamlit/secrets.toml` or via the Cloud UI.
    # For local development, you can create a `.streamlit/secrets.toml` file
    # containing:
    #   [credentials]
    #   username = "your_username"
    #   password = "your_password"
    # If no secrets are provided, the fallback credentials are user='admin'
    # and password='password'.
    default_user = 'admin'
    default_pass = 'password'
    creds = {}
    if 'credentials' in st.secrets:
        creds = st.secrets['credentials']
    username_secret = creds.get('username', default_user)
    password_secret = creds.get('password', default_pass)
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    # Render login form if not authenticated
    if not st.session_state['logged_in']:
        st.subheader("🔒 Please log in to continue")
        # Collect user credentials
        username_input = st.text_input("Username")
        password_input = st.text_input("Password", type="password")

        # When the user clicks the Login button, validate the credentials
        if st.button("Login"):
            if username_input == username_secret and password_input == password_secret:
                # Update session state to reflect successful login.  Once this
                # flag is True, the rest of the app will render on the next
                # iteration of the script.  We intentionally avoid calling
                # st.experimental_rerun() here because that API may not be
                # available in all Streamlit versions.  Instead, we rely on
                # Streamlit automatically rerunning the script after widget
                # interactions.  By not stopping execution below when the
                # flag flips, the rest of the app will load in the same run.
                st.session_state['logged_in'] = True
            else:
                st.error("Invalid username or password.")
        # If the user isn't logged in yet, halt the remainder of the app so
        # that only the login form shows.  Once the credentials have been
        # validated and `logged_in` is True, execution will continue past this
        # point on the next script run.
        if not st.session_state['logged_in']:
            st.stop()

    # -------------------------------------------------------------------------
    # Load workbook from the preloaded file or from session state
    # -------------------------------------------------------------------------
    default_file = 'DebtListNew.xlsx'
    try:
        cat_df, funds_df, loans_home_df, loans_friends_df = load_workbook(default_file)
    except Exception as e:
        st.error(f"Failed to load workbook: {e}")
        return

    # Merge with any new data added via the Add Data page
    cat_data = cat_df.copy()
    if 'new_cat_data' in st.session_state:
        cat_data = pd.concat([cat_data, st.session_state['new_cat_data']], ignore_index=True)

    funds_data = funds_df.copy()
    if 'new_funds_data' in st.session_state:
        funds_data = pd.concat([funds_data, st.session_state['new_funds_data']], ignore_index=True)

    loans_home_data = loans_home_df.copy()
    if 'new_loans_home' in st.session_state:
        loans_home_data = pd.concat([loans_home_data, st.session_state['new_loans_home']], ignore_index=True)

    loans_friends_data = loans_friends_df.copy()
    if 'new_loans_friends' in st.session_state:
        loans_friends_data = pd.concat([loans_friends_data, st.session_state['new_loans_friends']], ignore_index=True)

    # Sidebar navigation
    page = st.sidebar.selectbox(
        "Navigation",
        ["Dashboard", "Add Data", "Funds & Loans"],
        index=0,
    )
    if page == "Dashboard":
        show_dashboard(cat_data)
    elif page == "Add Data":
        show_add_data(cat_df, funds_df, loans_home_df, loans_friends_df, default_file)
    elif page == "Funds & Loans":
        show_funds_loans(funds_df, loans_home_df, loans_friends_df)


if __name__ == '__main__':
    main()