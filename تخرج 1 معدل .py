import cv2
import mediapipe as mp
import pygame
import requests
import time

# -----------------------------------
# إعدادات بوت تلغرام
# -----------------------------------
TOKEN = "8267641853:AAFej1EJy-CRdt01i-zyaNDHv9MajboJMmY"
CHAT_ID = "767312801"

def send_telegram_message(text):
    print("📤 ارسال تلغرام...")
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        data = {"chat_id": CHAT_ID, "text": text}
        r = requests.post(url, data=data, timeout=5)
        print("status:", r.status_code)
        print("response:", r.text)
    except Exception as e:
        print("Telegram Error:", e)

# -----------------------------------
# تشغيل الصوت
# -----------------------------------
pygame.mixer.init()

def play_sound(filename):
    try:
        pygame.mixer.music.load(filename)
        pygame.mixer.music.play()
    except Exception as e:
        print("خطأ في الصوت:", e)

# -----------------------------------
# mediapipe
# -----------------------------------
mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

hands = mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.6,
    min_tracking_confidence=0.6
)

def get_fingers_status(landmarks):
    finger_tips = [8, 12, 16, 20]
    finger_bases = [6, 10, 14, 18]
    fingers_open = []

    for tip, base in zip(finger_tips, finger_bases):
        fingers_open.append(1 if landmarks[tip].y < landmarks[base].y else 0)

    thumb_open = landmarks[4].x < landmarks[3].x
    fingers_open.insert(0, 1 if thumb_open else 0)
    return fingers_open

# -----------------------------------
# متغيرات الحركة
# -----------------------------------
movement_lr = 0
movement_ud = 0
last_direction_lr = None
last_direction_ud = None
last_x = None
last_y = None

start_time = time.time()
last_command_time = 0

# -----------------------------------
# الكاميرا
# -----------------------------------
cap = cv2.VideoCapture(0)


while True:
    success, frame = cap.read()
    if not success:
        break

    frame = cv2.flip(frame, 1)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb)

    if results.multi_hand_landmarks:
        for handLms in results.multi_hand_landmarks:
            mp_draw.draw_landmarks(frame, handLms, mp_hands.HAND_CONNECTIONS)

            landmarks = handLms.landmark
            fingers = get_fingers_status(landmarks)

            h, w, _ = frame.shape
            cx = int(landmarks[0].x * w)
            cy = int(landmarks[0].y * h)

            # -------- يمين / يسار --------
            if last_x is not None:
                if cx - last_x > 25 and last_direction_lr != "right":
                    movement_lr += 1
                    last_direction_lr = "right"
                elif last_x - cx > 25 and last_direction_lr != "left":
                    movement_lr += 1
                    last_direction_lr = "left"
            last_x = cx

            # -------- أعلى / أسفل --------
            if last_y is not None:
                if cy - last_y > 25 and last_direction_ud != "down":
                    movement_ud += 1
                    last_direction_ud = "down"
                elif last_y - cy > 25 and last_direction_ud != "up":
                    movement_ud += 1
                    last_direction_ud = "up"
            last_y = cy

            # -------- معالجة كل 4 ثواني --------
            if time.time() - start_time > 4 and time.time() - last_command_time > 6:

                # طلب ماء
                if movement_lr >= 3 and sum(fingers) >= 4:
                    print("🟦 طلب ماء")
                    play_sound("water.mp3")
                    send_telegram_message("🟦 طلب ماء")
                    last_command_time = time.time()

                # السرير غير مريح
                elif movement_lr >= 3 and sum(fingers) <= 1:
                    print("⚠️ السرير غير مريح")
                    play_sound("uncomfortable.mp3")
                    send_telegram_message("⚠️ السرير غير مريح")
                    last_command_time = time.time()

                # يوجد ألم
                elif movement_ud >= 3:
                    print("🔴 يوجد ألم")
                    play_sound("pain.mp3")
                    send_telegram_message("🔴 يوجد ألم")
                    last_command_time = time.time()

                movement_lr = 0
                movement_ud = 0
                last_direction_lr = None
                last_direction_ud = None
                start_time = time.time()

    cv2.imshow("Hand Control", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

    time.sleep(0.01)

cap.release()
cv2.destroyAllWindows()
