import cv2
from deepface import DeepFace
import numpy as np
import time

# URL of the Raspberry Pi video stream
stream_url = "http://<raspberrypi_ip>:8000/video_feed"  # replace with actual IP

# Load your face DB once
print("✅ Loading known faces...")
db_path = "known_images"  # folder containing known face images
model_name = "VGG-Face"  # you can also use "Facenet", "ArcFace" etc.

representations = DeepFace.find(
    img_path=[],  # empty because we’ll compare manually
    db_path=db_path,
    model_name=model_name,
    enforce_detection=False,
    silent=True,
)

# Extract embeddings for DB manually (for speed)
face_db = []
for entry in representations:
    face_db.append((entry['identity'], entry['embedding']))

print("✅ Face DB loaded:", len(face_db), "known faces")

# Start reading stream
cap = cv2.VideoCapture(stream_url)

if not cap.isOpened():
    print("❌ Cannot open video stream")
    exit()

model = DeepFace.build_model(model_name)

def recognize_face(frame):
    try:
        results = DeepFace.represent(frame, model_name=model_name, model=model, enforce_detection=False)
        if results:
            embedding = results[0]['embedding']

            # Compare with known embeddings
            for name, db_embedding in face_db:
                dist = DeepFace.distance.findCosineDistance(embedding, db_embedding)
                if dist < 0.4:  # threshold (tweak as needed)
                    return name.split("/")[-1].split(".")[0]  # display file name as name

    except Exception as e:
        print("Face detection error:", e)
    return "Unknown"


print("🎥 Starting face recognition...")
while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to grab frame")
        break

    frame = cv2.resize(frame, (640, 480))

    # Only every N frames to save CPU
    if int(time.time()) % 2 == 0:
        name = recognize_face(frame)
        cv2.putText(frame, name, (30, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    cv2.imshow("Hexapod Camera - Face Recognition", frame)

    if cv2.waitKey(1) == 27:  # ESC to quit
        break

cap.release()
cv2.destroyAllWindows()



