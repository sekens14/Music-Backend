from flask import Flask, request, send_file, jsonify
import yt_dlp
import io
import re
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

def validate_youtube_id(url):
    """Extract and validate 11-character YouTube ID"""
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11})',  # Standard URL
        r'youtu.be\/([0-9A-Za-z_-]{11})',  # Short URL
        r'embed\/([0-9A-Za-z_-]{11})',     # Embedded
        r'shorts\/([0-9A-Za-z_-]{11})'    # Shorts
    ]
    for pattern in patterns:
        match = re.search(pattern, url or "")
        if match:
            return match.group(1)
    return None

@app.route('/convert', methods=['GET'])
def convert():
    url = request.args.get('url')
    video_id = validate_youtube_id(url)
    
    if not video_id:
        return jsonify({
            "error": "Invalid URL",
            "required_format": "https://www.youtube.com/watch?v=11_DIGIT_ID",
            "example": "http://localhost:5000/convert?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        }), 400

    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'socket_timeout': 15,
        'extract_flat': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
        }],
        # Bypass restrictions
        'extractor_args': {
            'youtube': {
                'player_client': ['android'],
                'player_skip': ['configs']
            }
        },
        # Network resilience
        'retries': 3,
        'fragment_retries': 3,
        'skip_unavailable_fragments': True
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Get info first
            info = ydl.extract_info(f'https://youtu.be/{video_id}', download=False)
            
            # Download to memory
            buffer = io.BytesIO()
            ydl_opts['outtmpl'] = '-'
            with yt_dlp.YoutubeDL(ydl_opts) as ydl_download:
                audio_data = ydl_download.urlopen(info['url']).read()
                buffer.write(audio_data)
                buffer.seek(0)

            # Sanitize filename
            clean_title = re.sub(r'[\\/*?:"<>|]', "", info.get('title', 'audio'))[:50]
            
            return send_file(
                buffer,
                as_attachment=True,
                download_name=f"{clean_title}.mp3",
                mimetype="audio/mpeg"
            )

    except Exception as e:
        logger.error(f"Failed: {str(e)}")
        return jsonify({
            "error": "Conversion failed",
            "solution": [
                "1. Try a different video",
                "2. Use VPN if blocked",
                "3. Check https://github.com/yt-dlp/yt-dlp/issues if problem persists"
            ]
        }), 500

@app.route('/')
def home():
    return """
    <h1>Working YouTube MP3 Converter</h1>
    <h3>Test These Working Examples:</h3>
    <ul>
        <li><a href="/convert?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ">Example 1 (Rick Astley)</a></li>
        <li><a href="/convert?url=https://www.youtube.com/watch?v=LXb3EKWsInQ">Example 2 (Travel Video)</a></li>
    </ul>
    <p><strong>Note:</strong> Always use full 11-character video IDs</p>
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)