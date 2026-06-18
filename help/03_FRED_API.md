# FRED API Setup

This project retrieves macroeconomic indicators from the Federal Reserve Economic Data (FRED) platform.

To access FRED data programmatically, you must create a free FRED account and generate an API key.

Without a valid API key, the FRED ingestion pipeline will not be able to download economic indicators.

---

## Step 1 - Create a FRED Account

Visit the FRED website: https://fred.stlouisfed.org/

Create a free account using your email address.

---

## Step 2 - Request an API Key

After creating your account, request an API key at: https://fred.stlouisfed.org/docs/api/api_key.html

FRED will generate a unique API key associated with your account.

Keep this key private and do not commit it to source control.

---

## Step 3 - Configure the Environment File

Create a `.env` file in the root directory of the project:

```text
financial-risk-copilot/
├── .env
├── data/
├── src/
└── README.md
```

Add your API key to the .env file:

```env
FRED_API_KEY=your_api_key_here
```

Example:

```env
FRED_API_KEY=abcdefghijklmnopqrstuvwxyz123456
```

---

## Step 4 - Verify the Configuration

Run the FRED pipeline test:

```bash
python src/tests/test_fred_pipeline.py
```

If the configuration is correct, the pipeline should:

1. Download economic indicators from FRED.
2. Persist the data into the SQLite database.
3. Retrieve stored records from the database.
4. Display sample observations in the terminal.

Expected output:

```text
Retrieving FRED indicators...
Saving FRED indicators to SQLite...
Reading GDP from SQLite...
Rows retrieved for GDP: XXXX
FRED pipeline test completed successfully.
```

---

## Troubleshooting

### Missing API Key

If you see an error similar to:

```text
ValueError: FRED_API_KEY not found.
```

Verify that:

* The `.env` file exists in the project root.
* The variable name is exactly `FRED_API_KEY`.
* The API key value is valid.
* The application is being executed from the project's Python environment.

### Invalid API Key

If the API returns authentication errors, generate a new API key from the FRED website and update the `.env` file.
