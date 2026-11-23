import os
from app import create_app
from app.config import Config

app = create_app()

if __name__ == "__main__":
    host = os.getenv("HOST", Config.HOST)
    port = int(os.getenv("PORT", Config.PORT))
    print(f"==================================================")
    print(f"  VISITOR PHOTO SLIDESHOW APPLICATION RUNNING")
    print(f"  Upload Kiosk (Visitors):  http://{host if host != '0.0.0.0' else 'localhost'}:{port}/")
    print(f"  TV Slideshow Display:     http://{host if host != '0.0.0.0' else 'localhost'}:{port}/display")
    print(f"  Privacy & Gallery:        http://{host if host != '0.0.0.0' else 'localhost'}:{port}/gallery")
    print(f"==================================================")
    # threaded=True enables concurrent handling of SSE streams and upload requests
    app.run(host=host, port=port, debug=Config.DEBUG, threaded=True)
