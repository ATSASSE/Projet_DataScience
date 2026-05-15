import cv2

# Définir le pipeline GStreamer
pipeline = "rtspsrc location=rtsp://192.168.0.75:8554/stream short-header=true ! rtpjitterbuffer latency=10 ! rtpjpegdepay ! jpegparse ! jpegdec ! videoconvert ! appsink"
cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)

# Vérifier si la capture de la caméra est ouverte
if not cap.isOpened():
  print("Erreur: Impossible d'ouvrir la capture vidéo.")
  exit()

# Lire et enregistrer l'image
ret, frame = cap.read()
if not ret:
  print("Erreur: Impossible de lire la trame.")
  exit()

# Enregistrer l'image
cv2.imwrite("image_1.png", frame)

# Libérer les ressources
cap.release()
cv2.destroyAllWindows()
