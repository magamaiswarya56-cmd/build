# BuildPay — Streamlit Edition

Smart Construction Worker Payroll Management System with worker directory, face-scan attendance prototype, manual attendance, SQLite storage, payroll estimates, and CSV exports.

## Run locally (Windows PowerShell)

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

Open the local URL shown in the terminal (usually http://localhost:8501).

## Deploy to Streamlit Community Cloud

1. Create a GitHub repository (for example `BuildPay-Streamlit`).
2. Extract this ZIP and upload the *files inside it* to the repository root. Do not upload only the ZIP.
3. Visit https://share.streamlit.io/ and sign in with GitHub.
4. Choose **Create app**, select your repository and `main` branch.
5. Set **Main file path** to `streamlit_app.py`, then deploy.
6. Give browser camera permission when prompted.

## Features
- Worker directory with seeded demo workers and add-worker form
- Camera photo capture using `st.camera_input`
- Face detection using OpenCV Haar cascade
- Demo face-template enrollment and approximate matching
- Attendance saved by date in SQLite
- Manual attendance, attendance CSV, payroll estimate and payroll CSV

## Demo credentials / sample data
- Worker demo IDs are listed in the Workers page.
- Demo worker PIN: `1234`.

## Important limitations
- This is an academic prototype. The face template comparison is approximate and is **not reliable biometric identity verification**; it has no liveness detection and can be fooled by a photo. Do not use it for actual payroll, site access or decisions affecting workers.
- Streamlit Community Cloud's local filesystem is not guaranteed persistent. SQLite data stored in the app folder can be lost after restart/redeploy. Use a persistent managed database for real deployment.
- Demo PINs are not production authentication. Use secure password hashing, sessions/roles, HTTPS, audit logs, consent and retention controls before real use.
- Payroll numbers are illustrative estimates only; adapt them to approved company policies and applicable law.
