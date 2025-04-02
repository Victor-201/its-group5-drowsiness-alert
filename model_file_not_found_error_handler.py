MODEL_PATH = "shape_predictor_68_face_landmarks.dat"
if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(f"Không tìm thấy mô hình: {MODEL_PATH}")