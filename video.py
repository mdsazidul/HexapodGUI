from flask import Flask, Response
import cv2
from picamera2 import Picamera2
import numpy as np
import signal
import sys
import time
import logging
import os

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(
            '/home/sakhtar/Freenove_Big_Hexapod_Robot_Kit_for_Raspberry_Pi/Code/Sazid/HexapodGUI/video.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
picam2 = None


def initialize_camera(retries=3):
    """Initialize camera with retry logic"""
    global picam2

    for attempt in range(retries):
        try:
            logger.info(f"Initializing camera (attempt {attempt + 1}/{retries})...")

            # Close any existing camera instance
            if picam2 is not None:
                try:
                    picam2.stop()
                    picam2.close()
                except:
                    pass
                picam2 = None

            # Wait between attempts
            if attempt > 0:
                time.sleep(2)

            # Kill any hanging libcamera processes
            os.system("sudo pkill -f libcamera-hello 2>/dev/null")
            time.sleep(0.5)

            # Initialize Picamera2
            picam2 = Picamera2()

            # Configure for video streaming
            config = picam2.create_video_configuration(
                main={"size": (640, 480), "format": "RGB888"}
            )
            picam2.configure(config)

            # Start camera
            picam2.start()

            # Wait for camera to stabilize
            time.sleep(2)

            # Test capture
            test_frame = picam2.capture_array()
            if test_frame is not None and test_frame.size > 0:
                logger.info("✅ Camera initialized successfully")
                return True
            else:
                raise Exception("Test capture failed")

        except Exception as e:
            logger.error(f"❌ Camera initialization failed (attempt {attempt + 1}): {str(e)}")
            if picam2 is not None:
                try:
                    picam2.close()
                except:
                    pass
                picam2 = None

            if attempt < retries - 1:
                logger.info("Retrying...")
            else:
                logger.error("All camera initialization attempts failed")
                return False

    return False


def generate_frames():
    """Generate frames from camera with error handling"""
    global picam2

    while True:
        try:
            # Check if camera is initialized
            if picam2 is None:
                logger.warning("Camera not initialized, attempting to initialize...")
                if not initialize_camera():
                    time.sleep(5)
                    continue

            # Capture frame
            frame = picam2.capture_array()

            if frame is None or frame.size == 0:
                logger.warning("Empty frame captured")
                time.sleep(0.1)
                continue

            # Convert RGB to BGR if needed (Picamera2 returns RGB by default)
            if len(frame.shape) == 3 and frame.shape[2] == 3:
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

            # Encode frame as JPEG
            success, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])

            if not success:
                logger.warning("Frame encoding failed")
                continue

            frame_bytes = buffer.tobytes()

            # Yield frame in multipart format
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

            # Small delay to control frame rate (~30 FPS)
            time.sleep(0.033)

        except Exception as e:
            logger.error(f"Frame generation error: {str(e)}")
            # Try to recover by reinitializing camera
            if picam2 is not None:
                try:
                    picam2.stop()
                    picam2.close()
                except:
                    pass
                picam2 = None
            time.sleep(1)


@app.route('/video_feed')
def video_feed():
    """Video streaming route"""
    try:
        return Response(generate_frames(),
                        mimetype='multipart/x-mixed-replace; boundary=frame')
    except Exception as e:
        logger.error(f"Video feed error: {str(e)}")
        return "Video feed unavailable", 503


@app.route('/health')
def health():
    """Health check endpoint"""
    camera_ready = picam2 is not None
    return {
               'status': 'ok' if camera_ready else 'camera_not_ready',
               'camera': camera_ready
           }, 200 if camera_ready else 503


@app.route('/shutdown', methods=['POST'])
def shutdown():
    """Graceful shutdown endpoint"""
    cleanup(None, None)
    return "Shutting down...", 200


def cleanup(signum, frame):
    """Cleanup resources on shutdown"""
    global picam2

    logger.info("Cleaning up resources...")

    if picam2 is not None:
        try:
            picam2.stop()
            picam2.close()
            logger.info("Camera stopped and closed")
        except Exception as e:
            logger.error(f"Error during camera cleanup: {str(e)}")
        finally:
            picam2 = None

    cv2.destroyAllWindows()
    logger.info("Cleanup complete. Exiting...")

    sys.exit(0)


# Register signal handlers
signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)

if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("🎥 Video Stream Server Starting...")
    logger.info("=" * 60)

    # Initialize camera before starting Flask
    if not initialize_camera():
        logger.error("⚠️  Failed to initialize camera!")
        logger.error("⚠️  Server will start but video feed will be unavailable")
    else:
        logger.info("✅ Camera ready")

    try:
        logger.info("Starting Flask server on http://0.0.0.0:8080")
        logger.info("Video feed available at: http://0.0.0.0:8080/video_feed")
        logger.info("Health check at: http://0.0.0.0:8080/health")
        logger.info("-" * 60)

        # Run Flask server
        app.run(host='0.0.0.0', port=8080, threaded=True, debug=False)

    except KeyboardInterrupt:
        logger.info("\n🛑 Received shutdown signal")
        cleanup(None, None)
    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        cleanup(None, None)