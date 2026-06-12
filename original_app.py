#this original script removed entire background from object

import os
from pathlib import Path
from flask import Flask, request, render_template, send_file, jsonify
from werkzeug.utils import secure_filename
from PIL import Image
from rembg import remove
import uuid

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = Path("static/uploads")
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max

UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/replace', methods=['POST'])
def replace_background():
    if 'foreground' not in request.files or 'background' not in request.files:
        return jsonify({"error": "Both images are required"}), 400

    fg_file = request.files['foreground']
    bg_file = request.files['background']

    if fg_file.filename == '' or bg_file.filename == '':
        return jsonify({"error": "Both images must be selected"}), 400

    if not (allowed_file(fg_file.filename) and allowed_file(bg_file.filename)):
        return jsonify({"error": "Unsupported file type"}), 400

    try:
        # Generate unique filename
        session_id = str(uuid.uuid4())[:8]
        output_filename = f"result_{session_id}.png"
        output_path = UPLOAD_FOLDER / output_filename

        # Process images
        fg = Image.open(fg_file.stream).convert("RGBA")
        bg = Image.open(bg_file.stream).convert("RGBA")

        # Remove background
        fg_no_bg = remove(fg)

        # Resize background to match foreground
        bg_resized = bg.resize(fg_no_bg.size, Image.Resampling.LANCZOS)

        # Composite
        result = Image.alpha_composite(bg_resized, fg_no_bg)

        # Save
        result.save(output_path, format="PNG")

        return send_file(output_path, as_attachment=True, download_name="background_replaced.png")

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 8080)), debug=False)
