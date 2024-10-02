import os
import time
from flask import Flask, render_template, request, redirect, url_for, send_file, flash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs

# Load environment variables
load_dotenv()

# Retrieve the API key
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
if not ELEVENLABS_API_KEY:
    raise ValueError(
        "ELEVENLABS_API_KEY environment variable not found. "
        "Please set the API key in your environment variables."
    )

client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Required for flashing messages
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['TRANSLATED_FOLDER'] = 'data'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['TRANSLATED_FOLDER'], exist_ok=True)


def download_dubbed_file(dubbing_id: str, language_code: str) -> str:
    """
    Downloads the dubbed file for a given dubbing ID and language code.
    """
    dir_path = f"{app.config['TRANSLATED_FOLDER']}/{dubbing_id}"
    os.makedirs(dir_path, exist_ok=True)

    file_path = f"{dir_path}/{language_code}.mp4"
    with open(file_path, "wb") as file:
        for chunk in client.dubbing.get_dubbed_file(dubbing_id, language_code):
            file.write(chunk)

    return file_path


def wait_for_dubbing_completion(dubbing_id: str) -> bool:
    """
    Waits for the dubbing process to complete by periodically checking the status.
    """
    MAX_ATTEMPTS = 120
    CHECK_INTERVAL = 10  # In seconds

    for _ in range(MAX_ATTEMPTS):
        metadata = client.dubbing.get_dubbing_project_metadata(dubbing_id)
        if metadata.status == "dubbed":
            return True
        elif metadata.status == "dubbing":
            time.sleep(CHECK_INTERVAL)
        else:
            return False

    return False


def create_dub_from_file(input_file_path: str, file_format: str, source_language: str, target_language: str) -> str:
    """
    Dubs an audio or video file from one language to another and saves the output.
    """
    if not os.path.isfile(input_file_path):
        raise FileNotFoundError(f"The input file does not exist: {input_file_path}")

    with open(input_file_path, "rb") as audio_file:
        response = client.dubbing.dub_a_video_or_an_audio_file(
            file=(os.path.basename(input_file_path), audio_file, file_format),
            target_lang=target_language,
            source_lang=source_language,
            num_speakers=1,
            watermark=True,
        )

    dubbing_id = response.dubbing_id
    if wait_for_dubbing_completion(dubbing_id):
        output_file_path = download_dubbed_file(dubbing_id, target_language)
        return output_file_path
    else:
        return None


@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # File upload handling
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        
        if file:
            filename = secure_filename(file.filename)
            input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(input_path)

            # Display a message while processing
            flash('Dubbing in progress, please wait...')

            # Perform dubbing
            output_path = create_dub_from_file(input_path, "audio/mpeg", 'zh', 'en')
            if output_path:
                flash('Dubbing was successful!')
                return redirect(url_for('translated_file', file_path=output_path))
            else:
                flash('Dubbing failed or timed out.')
                return redirect(request.url)
    
    return render_template('upload.html')


@app.route('/translated')
def translated_file():
    file_path = request.args.get('file_path')
    if file_path and os.path.exists(file_path):
        # Create the correct file URL for the video player
        file_url = '/' + file_path.replace('\\', '/')
        return render_template('translated.html', file_url=file_url, file_path=file_path)
    else:
        flash('File not found')
        return redirect(url_for('upload_file'))


@app.route('/download')
def download_file():
    file_path = request.args.get('file_path')
    if file_path and os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        flash('File not found')
        return redirect(url_for('upload_file'))


if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
