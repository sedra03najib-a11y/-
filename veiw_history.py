# ==========================================
# Patient History Viewer (Doctor Interface)
# ==========================================
from db_handler import show_log_window

if __name__ == "__main__":
    print("📋 جاري تشغيل واجهة سجل المريض الطبي...")
    # فتح نافذة السجل لعرض البيانات المخزنة في patient_records.db
    show_log_window(patient_id=101, patient_name="سدرة")