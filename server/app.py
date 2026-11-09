import os
from pathlib import Path
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from preprocess import predict_dr_stage

app = Flask(__name__)

# Configuration
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", Path(__file__).parent / "uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MODEL_PATH = os.getenv("MODEL_PATH", str(Path(__file__).parent / "models" / "resnet_model.h5"))
IMG_SIZE = int(os.getenv("IMG_SIZE", "512"))

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "bmp", "tif", "tiff"}

# Lazy model loader
_model = None

def get_model():
    global _model
    if _model is None:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(
                f"Model weights not found at '{MODEL_PATH}'. "
                f"Please place model weights in the 'models/' folder or set MODEL_PATH."
            )
        import tensorflow as tf
        from keras.models import load_model
        print(f"Loading inference model from {MODEL_PATH}...")
        _model = load_model(MODEL_PATH)
    return _model

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/health", methods=["GET"])
def health_check():
    weights_loaded = os.path.exists(MODEL_PATH)
    return jsonify({
        "status": "healthy",
        "service": "GoMoDiarect-Inference-Server",
        "model_path": MODEL_PATH,
        "model_available": weights_loaded,
        "target_image_size": IMG_SIZE
    }), 200

@app.route("/predict", methods=["POST"])
def predict():
    if "image" not in request.files:
        return jsonify({"error": "No 'image' file provided in form-data payload."}), 400
        
    image_file = request.files["image"]
    if image_file.filename == "" or not allowed_file(image_file.filename):
        return jsonify({"error": "Invalid or missing filename. Supported: png, jpg, jpeg."}), 400
        
    filename = secure_filename(image_file.filename)
    saved_path = UPLOAD_DIR / filename
    image_file.save(saved_path)
    
    try:
        model = get_model()
        result = predict_dr_stage(str(saved_path), model=model, img_size=IMG_SIZE)
        return jsonify({
            "status": "success",
            "file": filename,
            "prediction": result
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "5000"))
    app.run(host=host, port=port, debug=False)
