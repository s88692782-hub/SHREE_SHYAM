# SHREE SHYAM Admin Panel

A Flask + SQLAlchemy admin and user panel for the SHREE SHYAM demo gaming project.

## Run locally

1. Open this folder in PyCharm or VS Code.
2. Create and activate a virtual environment.
3. Install dependencies with `pip install -r requirements.txt`.
4. Run `python app.py`.
5. Open `http://127.0.0.1:5000/login`.

Default local admin credentials for a fresh database: `admin` / `Admin@12345`. Change these before public deployment.

## Reports

System Reports includes Deposit Summary and Withdraw Summary with date filters, totals, transaction counts, search, and pagination. User deposit/withdraw requests initiated through WhatsApp are recorded as Pending before WhatsApp opens; actual payment settlement must be verified separately by an administrator/payment provider.

## Important

This project currently records demo/request transactions. Do not treat these screens as proof of real payment settlement. Configure secure production credentials, database backups, HTTPS, and authorized payment-provider callbacks before enabling real-money transactions.
