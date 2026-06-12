import os
from pathlib import Path
from flask import Flask, request, render_template, send_file, jsonify
from werkzeug.utils import secure_filename
from PIL import Image
import uuid
import cv2
import numpy as np

app = Flask(__name__)

UPLOAD_FOLDER = Path("static/uploads")
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024  # 20MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ----------------- Green Screen Removal -----------------
def remove_green_screen(image, lower_green=(40, 50, 50), upper_green=(80, 255, 255), tolerance=0):
    """
    Remove green screen and return RGBA image
    """
    img = np.array(image)
    if len(img.shape) == 2 or img.shape[2] == 4:
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2RGB)
    
    hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
    
    # Create mask
    mask = cv2.inRange(hsv, lower_green, upper_green)
    
    # Optional: Dilate/Erode to clean edges
    kernel = np.ones((3,3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    
    # Create alpha channel
    alpha = cv2.bitwise_not(mask)
    rgba = cv2.cvtColor(img, cv2.COLOR_RGB2RGBA)
    rgba[:, :, 3] = alpha
    
    return Image.fromarray(rgba)

# ----------------- Routes -----------------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/replace', methods=['POST'])
def replace_background():
    mode = request.form.get('mode', 'ai')  # 'ai' or 'greenscreen'

    if 'foreground' not in request.files or 'background' not in request.files:
        return jsonify({"error": "Both images are required"}), 400

    fg_file = request.files['foreground']
    bg_file = request.files['background']

    if fg_file.filename == '' or bg_file.filename == '':
        return jsonify({"error": "Both images must be selected"}), 400

    try:
        session_id = str(uuid.uuid4())[:8]
        output_path = UPLOAD_FOLDER / f"result_{session_id}.png"

        # Load images
        fg = Image.open(fg_file.stream).convert("RGB")
        bg = Image.open(bg_file.stream).convert("RGBA")

        if mode == 'greenscreen':
            # Green screen mode - user can tweak tolerance later
            fg_no_bg = remove_green_screen(fg)
        else:
            # Original AI mode
            from rembg import remove
            fg_no_bg = remove(fg.convert("RGBA"))

        # Resize background
        bg_resized = bg.resize(fg_no_bg.size, Image.Resampling.LANCZOS)

        # Composite
        result = Image.alpha_composite(bg_resized, fg_no_bg)

        result.save(output_path, format="PNG")

        return send_file(output_path, as_attachment=True, download_name="background_replaced.png")

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 8080)))
