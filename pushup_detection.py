import cv2
import mediapipe as mp
import math
from collections import deque

# Initialize MediaPipe Pose
mp_pose = mp.solutions.pose
pose = mp_pose.Pose()
mp_draw = mp.solutions.drawing_utils

# Function to calculate angle between 3 points
def calculate_angle(a, b, c):
    ba = [a[0]-b[0], a[1]-b[1]]
    bc = [c[0]-b[0], c[1]-b[1]]
    cosine_angle = (ba[0]*bc[0] + ba[1]*bc[1]) / (math.hypot(*ba)*math.hypot(*bc) + 1e-6)
    angle = math.degrees(math.acos(max(min(cosine_angle, 1), -1)))
    return angle

# Variables
cap = cv2.VideoCapture("video.mp4")
pushup_count = 0
state = "up"

# Angle smoothing buffer
angle_history = deque(maxlen=7)  # last 7 frames

# Setup video writer
frame_width = int(cap.get(3))
frame_height = int(cap.get(4))
fourcc = cv2.VideoWriter_fourcc(*'XVID')
out = cv2.VideoWriter('output_pushups.avi', fourcc, 30, (frame_width, frame_height))

# Full screen window
cv2.namedWindow("Push-up Detection", cv2.WND_PROP_FULLSCREEN)
cv2.setWindowProperty("Push-up Detection", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = pose.process(img_rgb)

    if result.pose_landmarks:
        landmarks = result.pose_landmarks.landmark

        # Get coordinates for both arms
        points = {}
        for side in ["LEFT", "RIGHT"]:
            shoulder = [landmarks[getattr(mp_pose.PoseLandmark, f"{side}_SHOULDER").value].x,
                        landmarks[getattr(mp_pose.PoseLandmark, f"{side}_SHOULDER").value].y]
            elbow = [landmarks[getattr(mp_pose.PoseLandmark, f"{side}_ELBOW").value].x,
                     landmarks[getattr(mp_pose.PoseLandmark, f"{side}_ELBOW").value].y]
            wrist = [landmarks[getattr(mp_pose.PoseLandmark, f"{side}_WRIST").value].x,
                     landmarks[getattr(mp_pose.PoseLandmark, f"{side}_WRIST").value].y]
            points[side] = {"shoulder": shoulder, "elbow": elbow, "wrist": wrist}

        # Calculate angles
        left_angle = calculate_angle(points["LEFT"]["shoulder"], points["LEFT"]["elbow"], points["LEFT"]["wrist"])
        right_angle = calculate_angle(points["RIGHT"]["shoulder"], points["RIGHT"]["elbow"], points["RIGHT"]["wrist"])
        avg_angle = (left_angle + right_angle) / 2

        angle_history.append(avg_angle)
        smooth_angle = sum(angle_history) / len(angle_history)

        # Push-up logic with hysteresis
        if smooth_angle < 105 and state == "up":   # Down condition
            state = "down"
        elif smooth_angle > 155 and state == "down":  # Up condition
            state = "up"
            pushup_count += 1

        # Feedback
        if smooth_angle > 150:
            feedback = "Arms straight (Top)"
        elif smooth_angle < 90:
            feedback = "Good depth (Bottom)"
        else:
            feedback = "In motion..."

        # landmarks + text
        mp_draw.draw_landmarks(frame, result.pose_landmarks, mp_pose.POSE_CONNECTIONS)
        cv2.putText(frame, f'Push-ups: {pushup_count}', (50,50), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0,0,255), 3)
        cv2.putText(frame, f'Form: {feedback}', (50,100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)

    # Write and show
    out.write(frame)
    cv2.imshow("Push-up Detection", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
out.release()
cv2.destroyAllWindows()