import sqlite3
from pathlib import Path
from datetime import date, datetime
import json
import numpy as np
import pandas as pd
import streamlit as st
import cv2

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "buildpay.db"
SITES = ["Orchid Residency · Site A", "Metro Tower · Site B", "Riverfront Villas · Site C"]
SEED = [
    ("23491A1213", "M.VYSHNAVI", "Mason", 850, SITES[0]),
    ("23491A1214", "M.AISWARYA", "Electrician", 950, SITES[1]),
    ("23491A1216", "N.GREESHMA", "Helper", 600, SITES[0]),
    ("23491A1218", "P.VARSHITHA", "Carpenter", 900, SITES[2]),
    ("23491A1222", "A.KOWSHIK REDDY", "Plumber", 1000, SITES[1]),
    ("23491A1254", "M.SANTHOSH", "Mason", 850, SITES[2]),
    ("BP1001", "Ravi Kumar", "Mason", 850, SITES[0]),
    ("BP1002", "Suresh Naidu", "Electrician", 950, SITES[1]),
    ("BP1003", "Lakshmi Devi", "Painter", 750, SITES[0]),
    ("BP1004", "Arjun Reddy", "Carpenter", 900, SITES[1]),
    ("BP1005", "Manoj Das", "Helper", 600, SITES[0]),
    ("BP1006", "Imran Khan", "Steel fixer", 875, SITES[2]),
]

st.set_page_config(page_title="BuildPay | Streamlit", page_icon="🏗️", layout="wide")

def db():
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS workers (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, role TEXT NOT NULL,
            site TEXT NOT NULL, wage REAL NOT NULL, pin TEXT NOT NULL DEFAULT '1234',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT, worker_id TEXT NOT NULL,
            work_date TEXT NOT NULL, status TEXT NOT NULL,
            marked_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(worker_id, work_date),
            FOREIGN KEY(worker_id) REFERENCES workers(id)
        );
        CREATE TABLE IF NOT EXISTS face_enrollments (
            worker_id TEXT PRIMARY KEY, descriptor TEXT NOT NULL,
            enrolled_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(worker_id) REFERENCES workers(id)
        );
        """)
        if con.execute("SELECT COUNT(*) FROM workers").fetchone()[0] == 0:
            con.executemany(
                "INSERT INTO workers(id,name,role,wage,site) VALUES(?,?,?,?,?)",
                [(wid, name, role, wage, site) for wid, name, role, wage, site in SEED]
            )

def workers_df():
    with db() as con:
        return pd.read_sql_query("SELECT id AS 'Worker ID', name AS Name, role AS Role, site AS Site, wage AS 'Daily Wage (₹)' FROM workers ORDER BY name", con)

def face_descriptor(uploaded):
    raw = np.frombuffer(uploaded.getvalue(), dtype=np.uint8)
    img = cv2.imdecode(raw, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not read this image. Try taking another photo.")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    detector = cv2.CascadeClassifier(cascade_path)
    faces = detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(70,70))
    if len(faces) == 0:
        return None, "No face detected. Face the camera with good lighting and try again."
    # For this educational demo, use the largest detected face.
    x, y, w, h = max(faces, key=lambda r: r[2] * r[3])
    crop = gray[y:y+h, x:x+w]
    crop = cv2.resize(crop, (64, 64), interpolation=cv2.INTER_AREA)
    # Normalize brightness; stored descriptor is a simple visual template, not a secure biometric embedding.
    crop = cv2.equalizeHist(crop)
    vector = crop.astype(np.float32).flatten()
    vector = (vector - vector.mean()) / (vector.std() + 1e-6)
    return vector.tolist(), None

def match_descriptor(candidate, stored_json):
    stored = np.asarray(json.loads(stored_json), dtype=np.float32)
    cand = np.asarray(candidate, dtype=np.float32)
    # Similarity is only a rough educational comparison and is not suitable for real identity verification.
    corr = float(np.dot(stored, cand) / ((np.linalg.norm(stored) * np.linalg.norm(cand)) + 1e-9))
    return corr

init_db()
st.markdown("""
<style>
.block-container {padding-top: 1.4rem; padding-bottom: 2rem;}
div[data-testid="stMetric"] {background:#f5f7fb;padding:14px;border-radius:12px;border:1px solid #e5e7eb;}
</style>
""", unsafe_allow_html=True)
st.title("🏗️ BuildPay")
st.caption("Smart Construction Worker Payroll Management System · Streamlit edition")

page = st.sidebar.radio("Navigation", ["Dashboard", "Workers", "Face Scan Attendance", "Attendance Records", "Payroll", "Deployment Notes"])
today = date.today().isoformat()

if page == "Dashboard":
    wdf = workers_df()
    with db() as con:
        att = pd.read_sql_query("SELECT status FROM attendance WHERE work_date=?", con, params=(today,))
        present = int((att["status"] == "Present").sum()) if not att.empty else 0
        marked = len(att)
        enrolled = con.execute("SELECT COUNT(*) FROM face_enrollments").fetchone()[0]
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Registered workers", len(wdf))
    c2.metric("Attendance marked today", marked)
    c3.metric("Present today", present)
    c4.metric("Face profiles enrolled", enrolled)
    st.subheader("Recent attendance")
    with db() as con:
        recent = pd.read_sql_query("""SELECT a.work_date AS Date, w.id AS 'Worker ID', w.name AS Worker,
          a.status AS Status, a.marked_at AS 'Marked at' FROM attendance a
          JOIN workers w ON w.id=a.worker_id ORDER BY a.marked_at DESC LIMIT 10""", con)
    st.dataframe(recent, use_container_width=True, hide_index=True)
    st.info("Demo credentials: worker IDs shown in Workers page, PIN 1234. This demo does not use production-grade authentication.")

elif page == "Workers":
    st.subheader("Worker directory")
    st.dataframe(workers_df(), use_container_width=True, hide_index=True)
    st.markdown("### Add worker")
    with st.form("add_worker", clear_on_submit=True):
        a,b = st.columns(2)
        wid = a.text_input("Worker ID", placeholder="e.g. BP1013")
        name = b.text_input("Full name")
        role = a.selectbox("Role", ["Helper", "Mason", "Electrician", "Carpenter", "Plumber", "Painter", "Steel fixer", "Site supervisor"])
        site = b.selectbox("Construction site", SITES)
        wage = a.number_input("Daily wage (₹)", min_value=1, value=700, step=50)
        pin = b.text_input("Demo PIN", value="1234")
        submit = st.form_submit_button("Add worker", type="primary")
        if submit:
            if not wid.strip() or not name.strip():
                st.error("Worker ID and name are required.")
            else:
                try:
                    with db() as con:
                        con.execute("INSERT INTO workers(id,name,role,site,wage,pin) VALUES(?,?,?,?,?,?)",
                                    (wid.strip(), name.strip(), role, site, float(wage), pin))
                    st.success("Worker added.")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("That Worker ID already exists.")

elif page == "Face Scan Attendance":
    st.subheader("📷 Face Scan Attendance")
    st.warning("Academic prototype only: the face template comparison is approximate and can misidentify people. Do not use this for real payroll or access control. Get informed consent before capturing biometric data.")
    with db() as con:
        wrows = con.execute("SELECT id,name FROM workers ORDER BY name").fetchall()
        enrolled_ids = {r["worker_id"] for r in con.execute("SELECT worker_id FROM face_enrollments").fetchall()}
    if not wrows:
        st.info("Add a worker first.")
    else:
        labels = {f'{r["name"]} ({r["id"]})': r["id"] for r in wrows}
        chosen_label = st.selectbox("Select worker for face enrollment", list(labels.keys()))
        chosen_id = labels[chosen_label]
        st.write("**Step 1 — Enroll:** take a clear photo for the selected worker. Only one face should be visible.")
        enrollment_photo = st.camera_input("Capture enrollment photo", key="enroll_camera")
        if st.button("Enroll / replace face template", type="primary"):
            if enrollment_photo is None:
                st.error("Capture a photo first.")
            else:
                descriptor, err = face_descriptor(enrollment_photo)
                if err:
                    st.error(err)
                else:
                    with db() as con:
                        con.execute("""INSERT INTO face_enrollments(worker_id,descriptor) VALUES(?,?)
                          ON CONFLICT(worker_id) DO UPDATE SET descriptor=excluded.descriptor, enrolled_at=CURRENT_TIMESTAMP""",
                          (chosen_id, json.dumps(descriptor)))
                    st.success("Face template saved for this demo. Now use the scan below.")
                    st.rerun()
        st.divider()
        st.write("**Step 2 — Scan:** capture a new photo. The app compares it with enrolled templates and marks attendance only when a rough similarity threshold is met.")
        scan_photo = st.camera_input("Capture attendance scan photo", key="scan_camera")
        if st.button("Scan and mark attendance"):
            if scan_photo is None:
                st.error("Capture a scan photo first.")
            else:
                candidate, err = face_descriptor(scan_photo)
                if err:
                    st.error(err)
                else:
                    with db() as con:
                        profiles = con.execute("""SELECT f.worker_id,f.descriptor,w.name FROM face_enrollments f
                            JOIN workers w ON w.id=f.worker_id""").fetchall()
                    if not profiles:
                        st.error("No face templates enrolled yet. Enroll a worker first.")
                    else:
                        scores = [(match_descriptor(candidate, p["descriptor"]), p) for p in profiles]
                        score, best = max(scores, key=lambda item: item[0])
                        st.write(f"Best approximate match score: `{score:.3f}`")
                        # Threshold is deliberately strict-ish but is not a guarantee of identity.
                        if score < 0.82:
                            st.error("No sufficiently similar enrolled face found. Try better lighting or re-enroll.")
                        else:
                            with db() as con:
                                con.execute("""INSERT INTO attendance(worker_id,work_date,status) VALUES(?,?,?)
                                    ON CONFLICT(worker_id,work_date) DO UPDATE SET status=excluded.status,marked_at=CURRENT_TIMESTAMP""",
                                    (best["worker_id"], today, "Present"))
                            st.success(f"Attendance marked PRESENT for {best['name']} ({best['worker_id']}) on {today}.")
                            st.rerun()
    st.caption(f"Enrolled worker profiles: {len(enrolled_ids)}")

elif page == "Attendance Records":
    st.subheader("Attendance records")
    selected_date = st.date_input("Select date", value=date.today()).isoformat()
    with db() as con:
        records = pd.read_sql_query("""SELECT a.work_date AS Date, w.id AS 'Worker ID', w.name AS Worker,
          a.status AS Status, a.marked_at AS 'Marked at' FROM attendance a
          JOIN workers w ON w.id=a.worker_id WHERE a.work_date=? ORDER BY w.name""", con, params=(selected_date,))
    st.dataframe(records, use_container_width=True, hide_index=True)
    st.download_button("Download attendance CSV", records.to_csv(index=False).encode("utf-8"), f"attendance_{selected_date}.csv", "text/csv")
    st.markdown("### Manual attendance")
    with db() as con:
        allw = con.execute("SELECT id,name FROM workers ORDER BY name").fetchall()
    labels = {f'{r["name"]} ({r["id"]})': r["id"] for r in allw}
    with st.form("manual_attendance"):
        worker_label = st.selectbox("Worker", list(labels.keys()))
        status = st.selectbox("Status", ["Present", "Late", "Absent"])
        save = st.form_submit_button("Save attendance")
        if save:
            with db() as con:
                con.execute("""INSERT INTO attendance(worker_id,work_date,status) VALUES(?,?,?)
                    ON CONFLICT(worker_id,work_date) DO UPDATE SET status=excluded.status,marked_at=CURRENT_TIMESTAMP""",
                    (labels[worker_label], selected_date, status))
            st.success("Attendance saved.")
            st.rerun()

elif page == "Payroll":
    st.subheader("Payroll estimates")
    a,b,c = st.columns(3)
    days = a.number_input("Paid days", min_value=0, max_value=31, value=26)
    overtime_hours = b.number_input("Overtime hours", min_value=0.0, value=6.0, step=1.0)
    deductions = c.number_input("Sample deductions (₹)", min_value=0.0, value=300.0, step=50.0)
    wdf = workers_df()
    with db() as con:
        attendance_counts = pd.read_sql_query("""SELECT worker_id, COUNT(*) AS present_days FROM attendance
          WHERE work_date >= date('now','start of month') AND work_date <= date('now')
          AND status IN ('Present','Late') GROUP BY worker_id""", con)
    wdf = wdf.merge(attendance_counts, left_on="Worker ID", right_on="worker_id", how="left").drop(columns=["worker_id"], errors="ignore")
    wdf["present_days"] = wdf["present_days"].fillna(0).astype(int)
    wdf["Base wages (₹)"] = wdf["Daily Wage (₹)"] * days
    wdf["Overtime pay (₹)"] = (wdf["Daily Wage (₹)"] / 8) * 1.5 * overtime_hours
    wdf["Sample deductions (₹)"] = deductions
    wdf["Estimated net (₹)"] = (wdf["Base wages (₹)"] + wdf["Overtime pay (₹)"] - deductions).clip(lower=0).round(2)
    st.dataframe(wdf, use_container_width=True, hide_index=True)
    st.download_button("Download payroll CSV", wdf.to_csv(index=False).encode("utf-8"), "buildpay_payroll_estimate.csv", "text/csv")
    st.caption("Illustrative estimates only. Configure actual company rules, attendance approvals and legal deductions before real use.")

else:
    st.subheader("Deploy BuildPay to Streamlit Community Cloud")
    st.markdown("""
1. Upload the **contents** of this ZIP (not the ZIP itself) to a new GitHub repository.
2. Open [share.streamlit.io](https://share.streamlit.io/) and sign in with GitHub.
3. Click **Create app**, choose your repository and `main` branch.
4. Set the main file path to `streamlit_app.py`, then click **Deploy**.
5. Allow camera permission in the browser when using Face Scan Attendance.

**Important hosting note:** Streamlit Community Cloud's local filesystem is not guaranteed persistent. This demo creates `buildpay.db` beside the app; data can be lost on restarts/redeploys. For a real hosted system, use a persistent external database and secure authentication.

**Demo logins for your project presentation:** Worker PIN is `1234`. This Streamlit edition currently focuses on worker directory, attendance, face scan prototype and payroll estimates; it is not a secure production payroll service.
""")
    st.code("pip install -r requirements.txt\nstreamlit run streamlit_app.py", language="powershell")
