import sqlite3, os
from flask import Flask, render_template, request, redirect, url_for, g, flash

app = Flask(__name__)
app.secret_key = "hms-secret"
DB = os.path.join(os.path.dirname(__file__), "hospital.db")

def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB); g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close(e=None):
    d = g.pop("db", None)
    if d: d.close()

SCHEMA = """
CREATE TABLE IF NOT EXISTS patients(id INTEGER PRIMARY KEY, name TEXT, age INT, gender TEXT, phone TEXT, address TEXT, disease TEXT, admitted TEXT);
CREATE TABLE IF NOT EXISTS doctors(id INTEGER PRIMARY KEY, name TEXT, specialization TEXT, phone TEXT, available TEXT, fee INT);
CREATE TABLE IF NOT EXISTS appointments(id INTEGER PRIMARY KEY, patient_id INT, doctor_id INT, date TEXT, time TEXT, status TEXT DEFAULT 'Scheduled');
CREATE TABLE IF NOT EXISTS bills(id INTEGER PRIMARY KEY, patient_id INT, description TEXT, amount INT, status TEXT DEFAULT 'Pending', date TEXT);
"""

def init():
    c = sqlite3.connect(DB); c.executescript(SCHEMA)
    if not c.execute("SELECT COUNT(*) FROM patients").fetchone()[0]:
        c.executemany("INSERT INTO patients(name,age,gender,phone,address,disease,admitted) VALUES(?,?,?,?,?,?,?)", [
            ("Rohan Deshmukh",34,"Male","98220 11234","Dharampeth, Nagpur","Typhoid","2026-10-20"),
            ("Anjali Verma",28,"Female","97650 44821","Sadar, Nagpur","Migraine","2026-10-22"),
            ("Suresh Patil",56,"Male","99230 77412","Manish Nagar, Nagpur","Hypertension","2026-10-23"),
            ("Priya Joshi",41,"Female","98900 33217","Sitabuldi, Nagpur","Diabetes","2026-10-25"),
            ("Aarav Mehta",9,"Male","90110 56743","Wardha Road, Nagpur","Viral Fever","2026-10-27")])
        c.executemany("INSERT INTO doctors(name,specialization,phone,available,fee) VALUES(?,?,?,?,?)", [
            ("Dr. Neha Kulkarni","Cardiologist","98811 20045","Mon - Fri",800),
            ("Dr. Amit Sharma","Neurologist","98812 30046","Mon - Sat",900),
            ("Dr. Sunita Rao","Pediatrician","98813 40047","Tue - Sun",500),
            ("Dr. Rajesh Iyer","General Physician","98814 50048","Mon - Sat",400)])
        c.executemany("INSERT INTO appointments(patient_id,doctor_id,date,time,status) VALUES(?,?,?,?,?)", [
            (1,4,"2026-10-28","10:00","Scheduled"),(2,2,"2026-10-28","11:30","Scheduled"),
            (3,1,"2026-10-29","09:30","Scheduled"),(5,3,"2026-10-27","16:00","Completed"),
            (4,4,"2026-10-30","12:15","Scheduled")])
        c.executemany("INSERT INTO bills(patient_id,description,amount,status,date) VALUES(?,?,?,?,?)", [
            (1,"Consultation + Lab tests",1850,"Paid","2026-10-21"),(2,"Consultation + MRI",5200,"Pending","2026-10-22"),
            (3,"ECG + Consultation",1400,"Pending","2026-10-23"),(5,"Consultation",500,"Paid","2026-10-27"),
            (4,"Blood sugar panel",950,"Paid","2026-10-25")])
    c.commit(); c.close()

@app.route("/")
def dashboard():
    d = db()
    stats = dict(
        patients=d.execute("SELECT COUNT(*) FROM patients").fetchone()[0],
        doctors=d.execute("SELECT COUNT(*) FROM doctors").fetchone()[0],
        appts=d.execute("SELECT COUNT(*) FROM appointments WHERE status='Scheduled'").fetchone()[0],
        revenue=d.execute("SELECT COALESCE(SUM(amount),0) FROM bills WHERE status='Paid'").fetchone()[0],
        pending=d.execute("SELECT COALESCE(SUM(amount),0) FROM bills WHERE status='Pending'").fetchone()[0])
    upcoming = d.execute("""SELECT a.*, p.name pname, dr.name dname, dr.specialization sp FROM appointments a
        JOIN patients p ON p.id=a.patient_id JOIN doctors dr ON dr.id=a.doctor_id
        WHERE a.status='Scheduled' ORDER BY date,time LIMIT 5""").fetchall()
    recent = d.execute("SELECT * FROM patients ORDER BY id DESC LIMIT 4").fetchall()
    return render_template("dashboard.html", s=stats, upcoming=upcoming, recent=recent, page="dashboard")

@app.route("/patients", methods=["GET","POST"])
def patients():
    d = db()
    if request.method == "POST":
        f = request.form
        d.execute("INSERT INTO patients(name,age,gender,phone,address,disease,admitted) VALUES(?,?,?,?,?,?,date('now'))",
                  (f["name"],f["age"],f["gender"],f["phone"],f["address"],f["disease"]))
        d.commit(); flash("Patient registered successfully"); return redirect(url_for("patients"))
    rows = d.execute("SELECT * FROM patients ORDER BY id DESC").fetchall()
    return render_template("patients.html", rows=rows, page="patients")

@app.route("/doctors", methods=["GET","POST"])
def doctors():
    d = db()
    if request.method == "POST":
        f = request.form
        d.execute("INSERT INTO doctors(name,specialization,phone,available,fee) VALUES(?,?,?,?,?)",
                  (f["name"],f["specialization"],f["phone"],f["available"],f["fee"]))
        d.commit(); flash("Doctor added successfully"); return redirect(url_for("doctors"))
    return render_template("doctors.html", rows=d.execute("SELECT * FROM doctors").fetchall(), page="doctors")

@app.route("/appointments", methods=["GET","POST"])
def appointments():
    d = db()
    if request.method == "POST":
        f = request.form
        d.execute("INSERT INTO appointments(patient_id,doctor_id,date,time) VALUES(?,?,?,?)",
                  (f["patient_id"],f["doctor_id"],f["date"],f["time"]))
        d.commit(); flash("Appointment booked"); return redirect(url_for("appointments"))
    rows = d.execute("""SELECT a.*, p.name pname, dr.name dname, dr.specialization sp FROM appointments a
        JOIN patients p ON p.id=a.patient_id JOIN doctors dr ON dr.id=a.doctor_id ORDER BY date DESC,time""").fetchall()
    return render_template("appointments.html", rows=rows, pts=d.execute("SELECT id,name FROM patients").fetchall(),
                           drs=d.execute("SELECT id,name,specialization FROM doctors").fetchall(), page="appointments")

@app.route("/billing", methods=["GET","POST"])
def billing():
    d = db()
    if request.method == "POST":
        f = request.form
        d.execute("INSERT INTO bills(patient_id,description,amount,date) VALUES(?,?,?,date('now'))",
                  (f["patient_id"],f["description"],f["amount"]))
        d.commit(); flash("Bill generated"); return redirect(url_for("billing"))
    rows = d.execute("SELECT b.*, p.name pname FROM bills b JOIN patients p ON p.id=b.patient_id ORDER BY b.id DESC").fetchall()
    return render_template("billing.html", rows=rows, pts=d.execute("SELECT id,name FROM patients").fetchall(), page="billing")

@app.route("/pay/<int:i>")
def pay(i):
    d = db(); d.execute("UPDATE bills SET status='Paid' WHERE id=?", (i,)); d.commit()
    flash("Payment recorded"); return redirect(url_for("billing"))

@app.route("/search")
def search():
    q = request.args.get("q","").strip(); like = f"%{q}%"; d = db()
    pts = d.execute("SELECT * FROM patients WHERE name LIKE ? OR disease LIKE ? OR phone LIKE ?", (like,like,like)).fetchall()
    drs = d.execute("SELECT * FROM doctors WHERE name LIKE ? OR specialization LIKE ?", (like,like)).fetchall()
    return render_template("search.html", q=q, pts=pts, drs=drs, page="search")

if __name__ == "__main__":
    init(); app.run(debug=True)
