import sqlite3
import tkinter as tk
from tkinter import ttk
from datetime import datetime, timedelta

DB_NAME = 'patient_records.db'

# 🟢 التعديل الأنسب: تحديد المدة بـ 8 ساعات لتوافقها مع مناوبة الطبيب/الممرض
FIXED_WINDOW_HOURS = 8


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS patient_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER,
            patient_name TEXT,
            request_type TEXT,
            timestamp TEXT,
            duration_hours INTEGER DEFAULT 8  -- المدة الثابتة للمناوبة
        )
    ''')
    conn.commit()
    conn.close()


def log_request(patient_id, patient_name, request_type, duration_hours=FIXED_WINDOW_HOURS):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute('''
        INSERT INTO patient_requests (patient_id, patient_name, request_type, timestamp, duration_hours)
        VALUES (?, ?, ?, ?, ?)
    ''', (patient_id, patient_name, request_type, now_str, duration_hours))

    conn.commit()
    conn.close()
    print(f"💾 [تم التسجيل]: {patient_name} - {request_type} ({now_str})")


def generate_clinical_insights(rows):
    """تحليل سجل الطلبات واستخراج توصيات طبية ضمن مناوبة الـ 8 ساعات الأخيرة"""
    if not rows:
        return f"ℹ️ لا توجد طلبات مسجلة خلال مناوبة الـ {FIXED_WINDOW_HOURS} ساعات الأخيرة."

    counts = {}
    for row in rows:
        req = row[0]
        counts[req] = counts.get(req, 0) + 1

    insights = []

    # 1. تحليل الجوع والتغذية
    hunger_count = sum(count for req, count in counts.items() if "جوع" in req or "طعام" in req)
    if hunger_count >= 3:
        insights.append(f"🍔 **مؤشر تغذية**: تكرر طلب (الشعور بالجوع) {hunger_count} مرات خلال المناوبة الحالية ({FIXED_WINDOW_HOURS} ساعات). يُوصى ببدائل غذائية.")

    # 2. تحليل الألم والطلب الطبي
    pain_count = sum(count for req, count in counts.items() if "ألم" in req or "طبيب" in req)
    if pain_count >= 2:  # خفض الحد الأدنى إلى 2 لأن المدة أصبحت 8 ساعات
        insights.append(f"⚠️ **مؤشر ألم مرتفع**: تكرر طلب (ألم/طبيب) {pain_count} مرات خلال المناوبة. يُوصى بتقييم المسكن.")

    # 3. تحليل الوضعية والراحة
    bed_count = sum(count for req, count in counts.items() if "السرير" in req or "راحة" in req)
    if bed_count >= 3:
        insights.append("🛏️ **عدم راحة جسدية**: طلبات متكررة لتعديل السرير خلال المناوبة. يُوصى بتغيير وضعية المريض.")

    # 4. تحليل الحالة النفسية
    psych_count = sum(count for req, count in counts.items() if "قلق" in req or "عائلة" in req)
    if psych_count >= 2:
        insights.append("🧠 **دعم نفسي مطلوب**: ارتفاع إشارات القلق أو طلب الأهل خلال المناوبة الحالية.")

    if not insights:
        insights.append(f"✅ **حالة المريض مستقرة**: جميع الطلبات خلال الـ {FIXED_WINDOW_HOURS} ساعات الأخيرة ضمن المعدل الطبيعي.")

    return "\n".join(insights)


def show_log_window(patient_id=101, patient_name="سدرة"):
    window = tk.Tk()
    window.title("📋 سجل وتقارير المريض الطبية - Clinical Decision Support")
    window.geometry("700x650")
    window.configure(bg="#1a202c")

    title_label = tk.Label(
        window,
        text=f"تقرير متابعة المريض: {patient_name} (ID: {patient_id})",
        font=("Arial", 14, "bold"),
        bg="#1a202c",
        fg="#ffffff"
    )
    title_label.pack(pady=10)

    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Treeview", background="#edf2f7", foreground="#1a202c", rowheight=25, fieldbackground="#edf2f7", font=("Arial", 10))
    style.configure("Treeview.Heading", font=("Arial", 11, "bold"), background="#3182ce", foreground="white")

    tree = ttk.Treeview(window, columns=("Request", "Time"), show="headings", height=8)
    tree.heading("Request", text="نوع الطلب / الإيماءة")
    tree.heading("Time", text="الوقت والتاريخ")

    tree.column("Request", width=340, anchor="center")
    tree.column("Time", width=280, anchor="center")

    # 🟢 جلب البيانات المحددة بـ 8 ساعات الأخيرة من وقت الفتح الحالي
    time_limit = (datetime.now() - timedelta(hours=FIXED_WINDOW_HOURS)).strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT request_type, timestamp 
        FROM patient_requests 
        WHERE patient_id = ? AND timestamp >= ?
        ORDER BY id DESC
    ''', (patient_id, time_limit))
    rows = cursor.fetchall()
    conn.close()

    for row in rows:
        tree.insert("", "end", values=row)

    tree.pack(padx=20, pady=5)

    analytics_frame = tk.LabelFrame(
        window,
        text=f" 🩺 التحليل الذكي والتوصيات الطبية (آخر {FIXED_WINDOW_HOURS} ساعات - الشفت الحالي) ",
        font=("Arial", 11, "bold"),
        bg="#2d3748",
        fg="#63b3ed",
        padx=10,
        pady=10
    )
    analytics_frame.pack(fill="x", padx=20, pady=10)

    insights_text = generate_clinical_insights(rows)

    analytics_label = tk.Label(
        analytics_frame,
        text=insights_text,
        font=("Arial", 10),
        bg="#2d3748",
        fg="#e2e8f0",
        justify="left",
        anchor="w"
    )
    analytics_label.pack(fill="x")

    footer_frame = tk.Frame(window, bg="#1a202c")
    footer_frame.pack(fill="x", padx=20, pady=5)

    summary_label = tk.Label(
        footer_frame,
        text=f"إجمالي الطلبات (خلال الـ {FIXED_WINDOW_HOURS} ساعات الأخيرة): {len(rows)}",
        font=("Arial", 10, "bold"),
        bg="#1a202c",
        fg="#a0aec0"
    )
    summary_label.pack(side="left")

    btn_close = tk.Button(
        footer_frame,
        text="إغلاق التقرير",
        command=window.destroy,
        font=("Arial", 10, "bold"),
        bg="#e53e3e",
        fg="white",
        padx=15
    )
    btn_close.pack(side="right")

    window.mainloop()