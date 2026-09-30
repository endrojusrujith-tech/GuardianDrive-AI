import cv2

# Path to the face detection model
model_path = "models/face_detection_yunet_2023mar.onnx"

# Create the face detector
detector = cv2.FaceDetectorYN.create(
    model_path,
    "",
    (320, 320),
    0.9,
    0.3,
    5000
)

# Open camera
camera = cv2.VideoCapture(0)

while True:

    # Read frame
    ret, frame = camera.read()

    if not ret:
        print("Camera could not be opened")
        break

    # Get frame dimensions
    height, width = frame.shape[:2]

    # Tell detector the current image size
    detector.setInputSize((width, height))

    # Detect faces
    _, faces = detector.detect(frame)

    # Draw results
    if faces is not None:

        for face in faces:

            x, y, w, h = face[:4].astype(int)

            # Draw face rectangle
            cv2.rectangle(
                frame,
                (x, y),
                (x + w, y + h),
                (0, 255, 0),
                2
            )

            # Display label
            cv2.putText(
                frame,
                "Driver Face",
                (x, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )

    # Show camera
    cv2.imshow(
        "Guardian Drive AI - Face Detection",
        frame
    )

    # Press Q to exit
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

camera.release()
cv2.destroyAllWindows()