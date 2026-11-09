import os
import cv2
import numpy as np
from PIL import Image

DR_CLASSES = {
    0: {"name": "No Diabetic Retinopathy", "code": "Grade 0"},
    1: {"name": "Mild Non-Proliferative DR", "code": "Grade 1"},
    2: {"name": "Moderate Non-Proliferative DR", "code": "Grade 2"},
    3: {"name": "Severe Non-Proliferative DR", "code": "Grade 3"},
    4: {"name": "Proliferative DR", "code": "Grade 4"}
}

def preprocess_retinal_image(img_path, img_size=512):
    """
    Load retinal fundus capture, convert to single-channel luminance,
    stack into a 3-channel uniform tensor, resize, and normalize to [0, 1].
    """
    if not os.path.exists(img_path):
        raise FileNotFoundError(f"Image file not found: {img_path}")
        
    image = Image.open(img_path).convert("L")
    gray_arr = np.array(image)
    
    # 3-channel identical mapping
    t3channel_image_array = np.stack((gray_arr,) * 3, axis=-1)
    t3channel_image = Image.fromarray(t3channel_image_array)
    
    temp = np.asarray(t3channel_image)
    temp = cv2.resize(temp, (img_size, img_size), interpolation=cv2.INTER_AREA)
    normalized = temp / 255.0
    tensor = np.expand_dims(normalized, axis=0)
    
    return t3channel_image, tensor

def predict_dr_stage(file_path, model, img_size=512):
    """
    Run forward pass and return predicted class, label, and raw scores.
    """
    _, tensor = preprocess_retinal_image(file_path, img_size=img_size)
    raw_prediction = model.predict(tensor)
    
    # Handle both classification (argmax) and regression outputs
    if raw_prediction.shape[-1] == 1:
        # Regression formulation
        score = float(raw_prediction[0][0])
        grade = int(np.clip(np.round(score), 0, 4))
        probs = [score]
    else:
        # Multi-class classification formulation
        probs = raw_prediction[0].tolist()
        grade = int(np.argmax(raw_prediction[0]))
        
    class_info = DR_CLASSES.get(grade, {"name": "Unknown", "code": f"Grade {grade}"})
    
    return {
        "grade": grade,
        "classification": class_info["name"],
        "stage_code": class_info["code"],
        "probabilities": probs
    }
