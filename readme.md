
🎬 AI Video Dubbing 🎬

This is a Flask web application that allows users to automatically translate a video's content from one language to another using the ElevenLabs API.

## Prerequisites
- Python 3.7+
- An [ElevenLabs](https://elevenlabs.com) API key.

## Setup Instructions

1. **Clone the repository:**
   ```
   git clone https://github.com/PaulHex6/VideoDubbing.git
   cd VideoDubbing
   ```

2. **Create a virtual environment:**
   ```
   python3 -m venv venv
   ```

3. **Activate the virtual environment:**
   - On Windows:
     ```
     venv\Scripts\activate
     ```
   - On macOS/Linux:
     ```
     source venv/bin/activate
     ```

4. **Install the required packages:**
   ```
   pip install -r requirements.txt
   ```

5. **Set up environment variables:**
   - Create a `.env` file in the project directory.
   - Add your ElevenLabs API key to the `.env` file:
     ```
     ELEVENLABS_API_KEY=your_api_key_here
     ```

6. **Run the application:**
   ```
   python app.py
   ```

7. **Access the application:**
   - Open a web browser and navigate to `http://127.0.0.1:5000/`.

## Usage
- Upload an MP4 file.
- The application will process the video and translate its content to the target language.
- Download the translated video once the process is complete.

## License
This project is licensed under the MIT License.
