from flask import Flask, render_template, request, redirect, url_for, send_file, flash
from flask_sqlalchemy import SQLAlchemy
import os
import time
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs

# Load environment variables
load_dotenv()
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
if not ELEVENLABS_API_KEY:
    raise ValueError("ELEVENLABS_API_KEY environment variable not found. Please set the API key.")

client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['TRANSLATED_FOLDER'] = 'data'

# Create folders if they don't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['TRANSLATED_FOLDER'], exist_ok=True)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///video_files.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy
db = SQLAlchemy(app)

class VideoFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(150), nullable=False)
    file_path = db.Column(db.String(300), nullable=False)
    dubbing_id = db.Column(db.String(100), nullable=True)

# Create the database and tables
with app.app_context():
    db.create_all()


def download_dubbed_file(dubbing_id, language_code):
    dir_path = os.path.join(app.config['TRANSLATED_FOLDER'], dubbing_id)
    os.makedirs(dir_path, exist_ok=True)
    file_path = os.path.join(dir_path, f"{language_code}.mp4")
    with open(file_path, "wb") as file:
        for chunk in client.dubbing.get_dubbed_file(dubbing_id, language_code):
            file.write(chunk)
    return file_path

def wait_for_dubbing_completion(dubbing_id):
    MAX_ATTEMPTS = 120
    CHECK_INTERVAL = 10
    for _ in range(MAX_ATTEMPTS):
        metadata = client.dubbing.get_dubbing_project_metadata(dubbing_id)
        if metadata.status == "dubbed":
            return True
        elif metadata.status == "dubbing":
            time.sleep(CHECK_INTERVAL)
        else:
            return False
    return False

def create_dub_from_file(input_file_path, file_format, source_language, target_language):
    with open(input_file_path, "rb") as audio_file:
        response = client.dubbing.dub_a_video_or_an_audio_file(
            file=(os.path.basename(input_file_path), audio_file, file_format),
            target_lang=target_language,
            source_lang=source_language,
            num_speakers=0,
            watermark=True,
        )
    dubbing_id = response.dubbing_id
    if wait_for_dubbing_completion(dubbing_id):
        return download_dubbed_file(dubbing_id, target_language)
    else:
        return None

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        file = request.files.get('file')
        if file and file.filename.endswith('.mp4'):
            filename = secure_filename(file.filename)
            input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(input_path)

            # Perform dubbing
            output_path = create_dub_from_file(input_path, "audio/mpeg", 'zh', 'en')
            if output_path:
                # Save file information to the database
                video_file = VideoFile(filename=filename, file_path=output_path)
                db.session.add(video_file)
                db.session.commit()

                # Redirect to the translated video page with the file ID
                return redirect(url_for('translated_file', file_id=video_file.id))
            else:
                return '<div class="alert alert-danger">Dubbing failed or timed out.</div>'
        return '<div class="alert alert-danger">Invalid file. Please upload an MP4 video.</div>'
    return render_template('index.html')

@app.route('/download')
def download_file():
    file_id = request.args.get('file_id')
    video_file = VideoFile.query.get(file_id)

    if video_file and os.path.exists(video_file.file_path):
        return send_file(video_file.file_path, as_attachment=True)
    else:
        flash('File not found')
        return redirect(url_for('upload_file'))

@app.route('/translated')
def translated_file():
    file_id = request.args.get('file_id')
    video_file = VideoFile.query.get(file_id)

    if video_file and os.path.exists(video_file.file_path):
        file_url = url_for('download_file', file_id=file_id)
        return render_template('translated.html', file_url=file_url, file_id=file_id)
    else:
        flash('File not found')
        return redirect(url_for('upload_file'))

@app.route('/history')
def view_history():
    # Fetch all video file records from the database
    video_files = VideoFile.query.all()
    return render_template('history.html', video_files=video_files)

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
