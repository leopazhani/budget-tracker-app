# Budget & Commitment Tracker Web App

This Streamlit-based web application helps you track monthly expenses, funds and
loans. It is designed to replicate and improve upon the structure of the
provided Excel workbook (`DebtListNew.xlsx`) by offering an interactive
dashboard, a simple data-entry interface and visual insights into your
finances.

## Features

* **Dashboard:**
  * Shows total planned vs actual spending for each month.
  * Highlights overspending by identifying categories where actual spending
    exceeds the planned amount.
  * Displays top spending categories and provides a per‑category trend
    analysis.
* **Funds & Loans:**
  * Summarises your funds (e.g. Home Commitments, Bangalore Commitment,
    Loan Commitment, etc.) and visualises their balances over time.
  * Displays outstanding loan balances both for home‑side loans and loans to
    friends.
* **Add Data:**
  * Supports uploading a new month’s Excel sheet in the same format as the
    existing workbook; the app will parse and append the data to the
    dashboard.
  * Allows manual entry of new monthly data via an editable table. You can
    add rows, edit category names and amounts, and save them to the session.

## Getting Started

### Prerequisites

This project requires Python 3.9+ and uses the following Python packages:

```
pandas
numpy
streamlit
```

Install the dependencies using `pip`:

```bash
pip install -r requirements.txt
```

Alternatively, install them manually:

```bash
pip install streamlit pandas numpy
```

### Running the App Locally

1. Clone or download this repository and place it in a directory of your choice.
2. Ensure the Excel workbook `DebtListNew.xlsx` is located in the project
   root (next to `app.py`).
3. From within the project directory, run the Streamlit app:

   ```bash
   streamlit run app.py
   ```

4. A new browser window should open automatically. If not, visit the URL
   displayed in your terminal (usually `http://localhost:8501`).

### Deployment on Streamlit Community Cloud

Streamlit Community Cloud is a free hosting platform specifically designed for
Streamlit apps.

1. Create a GitHub repository containing `app.py`, `DebtListNew.xlsx`, and
   `requirements.txt` (if included).
2. Sign up for Streamlit Community Cloud at
   [https://streamlit.io/cloud](https://streamlit.io/cloud) and click
   “Deploy an app”.
3. Connect your GitHub account and choose the repository and branch to deploy.
4. Specify `app.py` as the main file. Streamlit Cloud will automatically
   install the dependencies and deploy your app.
5. Once deployed, you’ll receive a shareable URL where anyone can access your
   dashboard.

### Deployment on Other Free Platforms

If you prefer a different hosting service (e.g. Replit, Vercel or
Render), ensure that the platform supports Python and long‑running web
applications. The basic steps usually involve creating a new project,
uploading your code, defining the start command (`streamlit run app.py`) and
providing the list of Python dependencies.

### Authentication

This application includes a simple username/password login to restrict access.
Credentials are read from Streamlit’s secret configuration. When running
locally, update the file `.streamlit/secrets.toml` with your desired
username and password:

```toml
[credentials]
username = "your_username"
password = "your_password"
```

On Streamlit Community Cloud you can define these secrets via the “Secrets”
tab of your deployed app. If no secrets are provided, the default username
is `admin` and the default password is `password`.

## Customisation

The parsing logic in `app.py` is tailored to the structure of the provided
workbook. If your Excel sheets differ in layout or you wish to track
additional data, you can modify the `parse_month_sheet` function accordingly.

The app stores new data only in the current session. For persistent
storage, consider integrating a database (e.g. SQLite) or saving updated
Excel files back to disk.

## Notes

* The current implementation does not overwrite or modify the original
  workbook. Any data you add via the app is stored in the session and
  combined with the preloaded workbook for display. Persisting changes will
  require additional code.
* For reliable month ordering, the app converts month strings like
  `Jul-25` or `May-25` into Python `datetime` objects using the first day of
  the month. Ensure your month names follow the `MMM-YY` format for
  consistent sorting.

## License

This project is provided for educational purposes and comes with no
warranty. You are free to adapt and extend it to suit your needs.