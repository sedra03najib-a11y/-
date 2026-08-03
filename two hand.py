# =========================
# IMPORTS
# =========================
import cv2
import mediapipe as mp
import numpy as np
import pygame
import requests
import threading
import time
import os

# استيراد وظائف قاعدة البيانات والواجهة المستقلة
from db_handler import init_db, log_request, show_log_window

# =========================
# INITIALIZE DATABASE
# =========================
init_db()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# =========================
# INITIALIZE AUDIO
# =========================
pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=2)

# =========================
# TELEGRAM CONFIGURATION
# =========================
TOKEN = "8267641853:AAFej1EJy-CRdt01i-zyaNDHv9MajboJMmY"
CHAT_ID = "767312801"

def send_telegram(message):
    def send():
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
            requests.post(url, data={"chat_id": CHAT_ID, "text": message}, timeout=5)
        except Exception as e:
            print("Telegram Error:", e)

    threading.Thread(target=send, daemon=True).start()

# =========================
# SOUND SYSTEM (ARABIC NAMES)
# =========================
def play_sound_file(command):
    try:
        sound_names = {
            1: "طوارئ",       # طوارئ / ضيق تنفس
            2: "جوع",        # شعور بالجوع / طعام
            3: "ماء",        # طلب ماء
            4: "راحة",       # السرير غير مريح
            5: "ألم",        # يوجد ألم
            6: "طبيب",       # طلب طبيب
            7: "عائلة",      # طلب عائلة
            8: "ملل"         # حالة نفسية:ملل
        }

        filename = sound_names.get(command)
        if not filename:
            return

        sounds_dir = os.path.join(BASE_DIR, "sounds")

        found_file = None
        if os.path.exists(sounds_dir):
            for file in os.listdir(sounds_dir):
                if file.startswith(filename):
                    found_file = os.path.join(sounds_dir, file)
                    break

        if found_file:
            sound = pygame.mixer.Sound(found_file)
            sound.play()
            print(f"🔊 تم تشغيل الصوت: {os.path.basename(found_file)}")
        else:
            print(f"⚠️ لم يتم العثور على ملف باسم: {filename}.mp3 داخل مجلد sounds")

    except Exception as e:
        print("Sound Error:", e)

# =========================
# MEDIAPIPE INITIALIZATION
# =========================
mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils
hands = mp_hands.Hands(
    max_num_hands=2,
    model_complexity=0,
    min_detection_confidence=0.6,
    min_tracking_confidence=0.5
)
print("✅ MediaPipe Ready")

# =========================
# FINGER COUNTING LOGIC
# =========================
def fingers_up(lm):
    fingers = []
    # Thumb
    if lm[4].x < lm[3].x:
        fingers.append(1)
    else:
        fingers.append(0)

    # بقية الأصابع
    tips = [8, 12, 16, 20]
    bases = [6, 10, 14, 18]
    for tip, base in zip(tips, bases):
        if lm[tip].y < lm[base].y:
            fingers.append(1)
        else:
            fingers.append(0)
    return fingers

# =========================
# COMMAND MAPS & MESSAGES
# =========================
messages = {
    0: "💤 سكون",
    1: "🚨 طوارئ / ضيق تنفس",
    2: "🍕 شعور بالجوع / طلب طعام",
    3: "💧 طلب ماء / شرب",
    4: "🛏️ السرير غير مريح / تعديل وضعية",
    5: "⚠️ يوجد ألم / شعور بألم",
    6: "👨‍⚕️ استدعاء طبيب",
    7: "😔 طلب عائلة / رؤية الأهل",
    8: "😰 حالة نفسية: ملل"
}
status = "Waiting..."


# =========================
# DRAW SIDEBAR INTERFACE (FIXED DIMENSIONS)
# =========================
def create_side_by_side_view(frame):
    # تغيير حجم فريم الكاميرا لضمان التوافق مع اللوحة الجانبية
    frame_resized = cv2.resize(frame, (640, 480))

    # إنشاء اللوحة الجانبية بعرض 300 وارتفاع 480
    sidebar = np.zeros((480, 300, 3), dtype=np.uint8)
    sidebar[:] = (30, 30, 30)

    # 1. العنوان الرئيسي
    cv2.putText(sidebar, "PATIENT", (30, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
    cv2.putText(sidebar, "ASSISTANT", (30, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

    cv2.line(sidebar, (20, 140), (280, 140), (70, 70, 70), 2)

    # 2. حالة النظام
    cv2.putText(sidebar, "Status:", (25, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (180, 180, 180), 1)
    cv2.putText(sidebar, status, (25, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)

    # دمج الفريم المعدل حجماً مع الشريط الجانبي
    combined = np.hstack((frame_resized, sidebar))
    return combined
# =========================
# COMMAND EXECUTION
# =========================
last_command = -1
last_time = 0
COOLDOWN = 3

def execute_command(command):
    global status

    current = messages[command]
    print("Detected:", current)

    # 1. حفظ الطلب في قاعدة البيانات تلقائياً
    log_request(patient_id=101, patient_name="سدرة", request_type=current)

    status = "Sending..."

    # 2. تشغيل الصوت وإرسال التلغرام (مباشر وبدون AI)
    threading.Thread(target=play_sound_file, args=(command,), daemon=True).start()
    send_telegram(current)

    status = "Sent"
# =========================
# CAMERA SETUP
# =========================
CAMERA_INDEX = 1  # جربي 1 ثم 0 ثم 2 إذا لم تظهر الصورة مباشرة

print(f"Opening Camera Index {CAMERA_INDEX}...")
cap = cv2.VideoCapture(CAMERA_INDEX)

if not cap.isOpened():
    print("Trying without index fallback...")
    cap = cv2.VideoCapture(0)

# ضبط الأبعاد إجبارياً
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# التأكد من وصول أول فريم بنجاح
ret, test_frame = cap.read()
if not ret or test_frame is None:
    print("⚠️ الكاميرا المحددة لا ترسل صورة، تجربة الكاميرا التالية...")
    cap.release()
    cap = cv2.VideoCapture(0)


# =========================
# MAIN APPLICATION LOOP
# =========================
while True:
    ret, frame = cap.read()
    if not ret:
        print("Frame Error")
        break

    frame = cv2.flip(frame, 1)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = hands.process(rgb)

    command = None

    if result.multi_hand_landmarks:
        hands_count = len(result.multi_hand_landmarks)

        if hands_count == 1:
            hand = result.multi_hand_landmarks[0]
            mp_draw.draw_landmarks(frame, hand, mp_hands.HAND_CONNECTIONS)
            lm = hand.landmark
            count = sum(fingers_up(lm))
            if 1 <= count <= 5:
                command = count

        elif hands_count == 2:
            total = 0
            for hand in result.multi_hand_landmarks:
                mp_draw.draw_landmarks(frame, hand, mp_hands.HAND_CONNECTIONS)
                lm = hand.landmark
                total += sum(fingers_up(lm))
            if 6 <= total <= 8:
                command = total

    if command is not None:
        now = time.time()
        if command != last_command and now - last_time > COOLDOWN:
            execute_command(command)
            last_command = command
            last_time = now
    else:
        status = "Waiting..."

    display_view = create_side_by_side_view(frame)

    cv2.imshow("Patient Assistant System", display_view)

    # الخروج بضغط زر q
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# =========================
# CLEANUP & SHOW LOG WINDOW
# =========================
cap.release()
cv2.destroyAllWindows()
hands.close()
pygame.quit()
print("👋 Camera Closed Safely. Opening Patient History Log Window...")

