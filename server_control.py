# import threading
# import time
# import sys
# import socket
# import json
# import cv2
# import os
# import csv
# import datetime
# import pyttsx3
# import paramiko
# import subprocess
# import numpy as np
# from deepface import DeepFace
# import logging
# import logging.handlers
# from pathlib import Path
# from typing import Dict, Any, Optional
# from dataclasses import dataclass, asdict
# from enum import Enum
#
# from PyQt5 import QtWidgets, QtGui, QtCore
# from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect, QThread, pyqtSignal, QMutex, QObject
# from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QLabel,
#                              QVBoxLayout, QHBoxLayout, QWidget, QFrame, QGridLayout,
#                              QGroupBox, QProgressBar, QTextEdit, QSlider, QSplashScreen)
# from PyQt5.QtGui import QImage, QPixmap, QFont, QPalette, QLinearGradient, QBrush, QColor
#
# try:
#     from deepface import DeepFace
#
#     DEEPFACE_AVAILABLE = True
# except ImportError:
#     print("Warning: DeepFace not available. Face recognition will be disabled.")
#     DEEPFACE_AVAILABLE = False
#
# try:
#     import pyttsx3
#
#     TTS_AVAILABLE = True
#     tts_engine = pyttsx3.init()
#     tts_engine.setProperty('rate', 150)
#     tts_engine.setProperty('volume', 1.0)
# except ImportError:
#     print("Warning: pyttsx3 not available. TTS will be disabled.")
#     TTS_AVAILABLE = False
#
#
# # ==================== LOGGING SYSTEM ====================
#
# class LogLevel(Enum):
#     DEBUG = "DEBUG"
#     INFO = "INFO"
#     WARNING = "WARNING"
#     ERROR = "ERROR"
#     CRITICAL = "CRITICAL"
#
#
# class ComponentType(Enum):
#     FACE_RECOGNITION = "FACE_RECOGNITION"
#     VIDEO_STREAM = "VIDEO_STREAM"
#     ROBOT_CONTROL = "ROBOT_CONTROL"
#     SERVER_CONNECTION = "SERVER_CONNECTION"
#     CAMERA_MANAGEMENT = "CAMERA_MANAGEMENT"
#     SYSTEM = "SYSTEM"
#     GUI = "GUI"
#
#
# @dataclass
# class LogEntry:
#     timestamp: str
#     level: str
#     component: str
#     message: str
#     session_id: str
#     thread_id: str
#     extra_data: Dict[str, Any] = None
#
#
# class CameraResourceManager:
#     """Manages camera resources and prevents PID conflicts"""
#
#     def __init__(self, rpi_host: str, rpi_user: str, rpi_password: str, logger=None):
#         self.rpi_host = rpi_host
#         self.rpi_user = rpi_user
#         self.rpi_password = rpi_password
#         self.logger = logger or logging.getLogger(__name__)
#         self.camera_lock = threading.Lock()
#
#     def release_camera_resources(self) -> bool:
#         """Release all camera-related processes on Raspberry Pi"""
#         try:
#             with self.camera_lock:
#                 ssh = paramiko.SSHClient()
#                 ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
#                 ssh.connect(self.rpi_host, username=self.rpi_user,
#                             password=self.rpi_password, timeout=10)
#
#                 # Commands to kill camera processes
#                 kill_commands = [
#                     "sudo pkill -f libcamera",
#                     "sudo pkill -f raspistill",
#                     "sudo pkill -f raspivid",
#                     "sudo pkill -f video_server.py",
#                     "sudo pkill -f video_stream_server.py",
#                     "sudo pkill -f 'python.*8000'",
#                     "sudo pkill -f 'python.*camera'",
#                     "sudo fuser -k /dev/video0 2>/dev/null || true",
#                     "sudo modprobe -r bcm2835-v4l2 2>/dev/null || true",
#                     "sudo modprobe bcm2835-v4l2 2>/dev/null || true"
#                 ]
#
#                 for cmd in kill_commands:
#                     try:
#                         stdin, stdout, stderr = ssh.exec_command(cmd)
#                         stdout.read()  # Wait for command completion
#                         self.logger.info(f"Executed: {cmd}")
#                     except Exception as e:
#                         self.logger.warning(f"Command failed: {cmd} - {e}")
#
#                 ssh.close()
#                 time.sleep(2)  # Allow processes to fully terminate
#
#                 self.logger.info("Camera resources released successfully")
#                 return True
#
#         except Exception as e:
#             self.logger.error(f"Failed to release camera resources: {e}")
#             return False
#
#     def check_camera_availability(self) -> bool:
#         """Check if camera is available for use"""
#         try:
#             ssh = paramiko.SSHClient()
#             ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
#             ssh.connect(self.rpi_host, username=self.rpi_user,
#                         password=self.rpi_password, timeout=5)
#
#             # Check for camera processes
#             stdin, stdout, stderr = ssh.exec_command("lsof /dev/video0 2>/dev/null || echo 'available'")
#             result = stdout.read().decode().strip()
#
#             ssh.close()
#
#             available = "available" in result or len(result) == 0
#             self.logger.info(f"Camera availability check: {'Available' if available else 'In use'}")
#             return available
#
#         except Exception as e:
#             self.logger.error(f"Camera availability check failed: {e}")
#             return False
#
#
# class HexapodLogger:
#     """Comprehensive logging system for Hexapod Robot"""
#
#     def __init__(self, log_dir: str = "hexapod_logs", session_id: Optional[str] = None):
#         self.log_dir = Path(log_dir)
#         self.log_dir.mkdir(exist_ok=True)
#
#         self.session_id = session_id or self._generate_session_id()
#         self.loggers = {}
#         self.log_entries = []
#         self.lock = threading.Lock()
#
#         # Create session log file
#         self.session_log_file = self.log_dir / f"session_{self.session_id}.log"
#         self.json_log_file = self.log_dir / f"session_{self.session_id}.json"
#
#         # Setup formatters
#         self.detailed_formatter = logging.Formatter(
#             fmt='%(asctime)s | %(levelname)-8s | %(name)-20s | %(threadName)-15s | %(message)s',
#             datefmt='%Y-%m-%d %H:%M:%S'
#         )
#
#         self.simple_formatter = logging.Formatter(
#             fmt='%(asctime)s [%(levelname)s] %(message)s',
#             datefmt='%H:%M:%S'
#         )
#
#         # Setup main application logger
#         self.setup_main_logger()
#
#         # Component-specific loggers
#         self.setup_component_loggers()
#
#         # Start log monitoring thread
#         self.start_log_monitor()
#
#     def _generate_session_id(self) -> str:
#         """Generate unique session ID"""
#         return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
#
#     def setup_main_logger(self):
#         """Setup main application logger with multiple handlers"""
#         main_logger = logging.getLogger("HexapodMain")
#         main_logger.setLevel(logging.DEBUG)
#
#         # Clear any existing handlers
#         main_logger.handlers.clear()
#
#         # File handler for detailed logs
#         file_handler = logging.FileHandler(self.session_log_file)
#         file_handler.setLevel(logging.DEBUG)
#         file_handler.setFormatter(self.detailed_formatter)
#
#         # Rotating file handler for long-term storage
#         rotating_handler = logging.handlers.RotatingFileHandler(
#             self.log_dir / "hexapod.log",
#             maxBytes=10 * 1024 * 1024,  # 10MB
#             backupCount=5
#         )
#         rotating_handler.setLevel(logging.INFO)
#         rotating_handler.setFormatter(self.detailed_formatter)
#
#         # Console handler for immediate feedback
#         console_handler = logging.StreamHandler(sys.stdout)
#         console_handler.setLevel(logging.INFO)
#         console_handler.setFormatter(self.simple_formatter)
#
#         # Error file handler
#         error_handler = logging.FileHandler(self.log_dir / "errors.log")
#         error_handler.setLevel(logging.ERROR)
#         error_handler.setFormatter(self.detailed_formatter)
#
#         main_logger.addHandler(file_handler)
#         main_logger.addHandler(rotating_handler)
#         main_logger.addHandler(console_handler)
#         main_logger.addHandler(error_handler)
#
#         self.loggers["main"] = main_logger
#
#     def setup_component_loggers(self):
#         """Setup component-specific loggers"""
#         for component in ComponentType:
#             logger = logging.getLogger(f"Hexapod.{component.value}")
#             logger.setLevel(logging.DEBUG)
#             logger.handlers.clear()
#
#             # Component-specific file handler
#             component_file = self.log_dir / f"{component.value.lower()}.log"
#             file_handler = logging.FileHandler(component_file)
#             file_handler.setLevel(logging.DEBUG)
#             file_handler.setFormatter(self.detailed_formatter)
#
#             logger.addHandler(file_handler)
#             self.loggers[component.value] = logger
#
#     def log(self, level: LogLevel, component: ComponentType, message: str, **kwargs):
#         """Enhanced logging method with structured data"""
#         logger = self.loggers.get(component.value, self.loggers["main"])
#
#         # Create structured log entry
#         log_entry = LogEntry(
#             timestamp=datetime.datetime.now().isoformat(),
#             level=level.value,
#             component=component.value,
#             message=message,
#             session_id=self.session_id,
#             thread_id=threading.current_thread().name,
#             extra_data=kwargs if kwargs else None
#         )
#
#         # Store for JSON export
#         with self.lock:
#             self.log_entries.append(log_entry)
#
#         # Log to appropriate level
#         log_method = getattr(logger, level.value.lower())
#         log_method(message, extra=kwargs)
#
#         # Save to JSON periodically
#         if len(self.log_entries) % 10 == 0:
#             self.save_json_log()
#
#     def save_json_log(self):
#         """Save logs to JSON format for analysis"""
#         try:
#             with open(self.json_log_file, 'w') as f:
#                 json_data = [asdict(entry) for entry in self.log_entries]
#                 json.dump(json_data, f, indent=2)
#         except Exception as e:
#             self.loggers["main"].error(f"Failed to save JSON log: {e}")
#
#     def start_log_monitor(self):
#         """Start background thread to monitor and analyze logs"""
#
#         def monitor_logs():
#             while True:
#                 try:
#                     # Analyze recent errors
#                     recent_errors = [entry for entry in self.log_entries[-50:]
#                                      if entry.level in ["ERROR", "CRITICAL"]]
#
#                     if len(recent_errors) > 5:
#                         self.log(LogLevel.WARNING, ComponentType.SYSTEM,
#                                  f"High error rate detected: {len(recent_errors)} errors in last 50 entries")
#
#                     # Check for camera issues
#                     camera_errors = [entry for entry in self.log_entries[-20:]
#                                      if "camera" in entry.message.lower() or "video" in entry.message.lower()]
#
#                     if len(camera_errors) > 3:
#                         self.log(LogLevel.WARNING, ComponentType.CAMERA_MANAGEMENT,
#                                  "Camera-related issues detected, may need resource cleanup")
#
#                     time.sleep(30)  # Check every 30 seconds
#
#                 except Exception as e:
#                     self.loggers["main"].error(f"Log monitor error: {e}")
#                     time.sleep(60)
#
#         monitor_thread = threading.Thread(target=monitor_logs, daemon=True, name="LogMonitor")
#         monitor_thread.start()
#
#     def get_logger(self, component: ComponentType) -> logging.Logger:
#         """Get logger for specific component"""
#         return self.loggers.get(component.value, self.loggers["main"])
#
#
# # ==================== ORIGINAL COMPONENTS ====================
#
# # Initialize TTS engine
# tts_engine = pyttsx3.init()
# tts_engine.setProperty('rate', 150)
# tts_engine.setProperty('volume', 1.0)
#
#
# def speak_offline(message):
#     if TTS_AVAILABLE:
#         try:
#             tts_engine.say(message)
#             tts_engine.runAndWait()
#         except Exception as e:
#             print(f"TTS Error: {e}")
#     else:
#         print(f"TTS not available: {message}")
#
#
# def get_pi_ip():
#     try:
#         return socket.gethostbyname("raspberrypi.local")
#     except socket.gaierror:
#         return "192.168.1.173"  # Fallback IP
#
#
# def find_raspberry_pi_ip():
#     try:
#         hostname = "raspberrypi.local"
#         ip_address = socket.gethostbyname(hostname)
#         return ip_address
#     except socket.gaierror:
#         return get_pi_ip()
#
#
# class EnhancedFaceRecognitionWorker(QThread):  # Inherit from QThread, not QObject
#     frame_processed = pyqtSignal(np.ndarray)
#     recognition_result = pyqtSignal(str, tuple)
#     error_occurred = pyqtSignal(str)
#
#     def __init__(self, rpi_host, logger_system: HexapodLogger):
#         super().__init__()
#         self.rpi_host = rpi_host
#         self.logger_system = logger_system
#         self.logger = logger_system.get_logger(ComponentType.FACE_RECOGNITION)
#         self.camera_manager = CameraResourceManager(rpi_host, RPI_USER, RPI_PASSWORD, self.logger)
#         self.running = False
#         self.mutex = QMutex()
#
#     def run(self):
#         """Main thread execution - this replaces the blocking loop"""
#         if not DEEPFACE_AVAILABLE:
#             self.error_occurred.emit("DeepFace not available")
#             return
#
#         if self.start_recognition_with_camera_fix():
#             self.start_recognition()
#
#     def start_recognition_with_camera_fix(self):
#         """Start face recognition with automatic camera cleanup"""
#         try:
#             self.mutex.lock()
#
#             # Step 1: Release camera resources
#             self.logger_system.log(LogLevel.INFO, ComponentType.CAMERA_MANAGEMENT,
#                                    "Releasing camera resources before starting recognition")
#
#             if not self.camera_manager.release_camera_resources():
#                 self.error_occurred.emit("Failed to release camera resources")
#                 return False
#
#             # Step 2: Wait and verify camera availability
#             time.sleep(3)
#             if not self.camera_manager.check_camera_availability():
#                 self.error_occurred.emit("Camera still not available after cleanup")
#                 return False
#
#             # Step 3: Start video server
#             self.logger_system.log(LogLevel.INFO, ComponentType.VIDEO_STREAM,
#                                    "Starting video server on Raspberry Pi")
#
#             if not self._start_video_server():
#                 self.error_occurred.emit("Failed to start video server")
#                 return False
#
#             # Step 4: Start recognition
#             self.running = True
#             self.start_recognition()
#             return True
#
#         except Exception as e:
#             self.logger_system.log(LogLevel.ERROR, ComponentType.FACE_RECOGNITION,
#                                    f"Failed to start face recognition: {e}")
#             self.error_occurred.emit(f"Recognition startup failed: {e}")
#             return False
#         finally:
#             self.mutex.unlock()
#
#     def _start_video_server(self) -> bool:
#         """Start video server with proper error handling"""
#         try:
#             ssh = paramiko.SSHClient()
#             ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
#             ssh.connect(self.rpi_host, username=RPI_USER, password=RPI_PASSWORD, timeout=10)
#
#             # Ensure video server is not running
#             ssh.exec_command("pkill -f video_stream_server.py")
#             time.sleep(1)
#
#             # Start video server
#             command = (
#                 "source /home/sakhtar/Freenove_Big_Hexapod_Robot_Kit_for_Raspberry_Pi/Code/Sazid/HexapodGUI/myenv/bin/activate && "
#                 "nohup python /home/sakhtar/Freenove_Big_Hexapod_Robot_Kit_for_Raspberry_Pi/Code/Sazid/HexapodGUI/video_stream_server.py > video.log 2>&1 &"
#             )
#
#             stdin, stdout, stderr = ssh.exec_command(command)
#             ssh.close()
#
#             # Waiting for server to start
#             time.sleep(4)
#
#             # Verifying server is running
#             return self._verify_video_server()
#
#         except Exception as e:
#             self.logger_system.log(LogLevel.ERROR, ComponentType.VIDEO_STREAM,
#                                    f"Failed to start video server: {e}")
#             return False
#
#     def _verify_video_server(self) -> bool:
#         """Verify video server is accessible"""
#         try:
#             test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#             test_socket.settimeout(5)
#             result = test_socket.connect_ex((self.rpi_host, 8000))
#             test_socket.close()
#
#             if result == 0:
#                 self.logger_system.log(LogLevel.INFO, ComponentType.VIDEO_STREAM,
#                                        "Video server is accessible")
#                 return True
#             else:
#                 self.logger_system.log(LogLevel.ERROR, ComponentType.VIDEO_STREAM,
#                                        "Video server is not accessible")
#                 return False
#
#         except Exception as e:
#             self.logger_system.log(LogLevel.ERROR, ComponentType.VIDEO_STREAM,
#                                    f"Video server verification failed: {e}")
#             return False
#
#     def start_recognition(self):
#         """Start the face recognition process with enhanced logging"""
#         try:
#             stream_url = f"http://{self.rpi_host}:8000/video_feed"
#             cap = cv2.VideoCapture(stream_url)
#             cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
#
#             if not cap.isOpened():
#                 self.logger_system.log(LogLevel.ERROR, ComponentType.FACE_RECOGNITION,
#                                        "Failed to open video stream")
#                 self.error_occurred.emit("Failed to open video stream")
#                 return
#
#             face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
#
#             frame_count = 0
#             recognition_interval = 30
#             last_result = ("Unknown", (0, 0, 255))
#             recognition_count = 0
#
#             self.logger_system.log(LogLevel.INFO, ComponentType.FACE_RECOGNITION,
#                                    "Face recognition loop started successfully")
#
#             while self.running and cap.isOpened():
#                 ret, frame = cap.read()
#                 if not ret:
#                     time.sleep(0.1)
#                     continue
#
#                 # Resize frame for better performance
#                 height, width = frame.shape[:2]
#                 if width > 640:
#                     scale_factor = 640 / width
#                     new_width = int(width * scale_factor)
#                     new_height = int(height * scale_factor)
#                     frame = cv2.resize(frame, (new_width, new_height))
#
#                 frame_count += 1
#
#                 # Log progress every 100 frames
#                 if frame_count % 100 == 0:
#                     self.logger_system.log(LogLevel.DEBUG, ComponentType.FACE_RECOGNITION,
#                                            f"Processed {frame_count} frames, {recognition_count} recognitions")
#
#                 # Face detection (fast operation)
#                 try:
#                     gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
#                     faces = face_cascade.detectMultiScale(
#                         gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
#                     )
#
#                     # Only run recognition periodically and if faces detected
#                     if frame_count % recognition_interval == 0 and len(faces) > 0:
#                         try:
#                             result = DeepFace.find(
#                                 img_path=frame,
#                                 db_path="known_images",
#                                 model_name="Facenet",
#                                 enforce_detection=False,
#                                 distance_metric="cosine",
#                                 threshold=0.7,
#                                 silent=True
#                             )
#
#                             if len(result) > 0 and not result[0].empty:
#                                 identity_path = result[0].iloc[0]['identity']
#                                 filename = os.path.basename(identity_path)
#                                 label = os.path.splitext(filename)[0]
#                                 last_result = (label, (0, 255, 0))
#                                 recognition_count += 1
#
#                                 # Emit recognition result
#                                 self.recognition_result.emit(label, (0, 255, 0))
#
#                                 # Log recognition with enhanced data
#                                 self.logger_system.log(LogLevel.INFO, ComponentType.FACE_RECOGNITION,
#                                                        f"Face recognized: {label}",
#                                                        frame_number=frame_count,
#                                                        faces_detected=len(faces),
#                                                        recognition_count=recognition_count)
#
#                                 # Log recognition to CSV
#                                 try:
#                                     with open("recognition_log.csv", mode="a", newline='') as file:
#                                         writer = csv.writer(file)
#                                         writer.writerow([datetime.datetime.now(), "person1", label])
#                                 except Exception as csv_error:
#                                     self.logger_system.log(LogLevel.WARNING, ComponentType.FACE_RECOGNITION,
#                                                            f"CSV logging failed: {csv_error}")
#                             else:
#                                 last_result = ("Unknown", (0, 0, 255))
#
#                         except Exception as e:
#                             self.logger_system.log(LogLevel.ERROR, ComponentType.FACE_RECOGNITION,
#                                                    f"Recognition error: {str(e)}")
#                             self.error_occurred.emit(f"Recognition error: {str(e)}")
#                             last_result = ("Error", (255, 0, 0))
#
#                     # Draw face rectangles with last known result
#                     label, color = last_result
#                     for (x, y, w, h) in faces:
#                         cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
#                         cv2.putText(frame, label, (x, y - 10),
#                                     cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
#
#                     # Add processing indicator
#                     if frame_count % recognition_interval < 5:
#                         cv2.putText(frame, "Processing...", (10, 30),
#                                     cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
#
#                     # Emit processed frame
#                     self.frame_processed.emit(frame)
#
#                 except Exception as e:
#                     self.logger_system.log(LogLevel.ERROR, ComponentType.FACE_RECOGNITION,
#                                            f"Frame processing error: {str(e)}")
#                     self.error_occurred.emit(f"Frame processing error: {str(e)}")
#
#                 # Control frame rate
#                 time.sleep(0.033)  # ~30 FPS
#
#             cap.release()
#             self.logger_system.log(LogLevel.INFO, ComponentType.FACE_RECOGNITION,
#                                    f"Face recognition ended. Total frames: {frame_count}, Recognitions: {recognition_count}")
#
#         except Exception as e:
#             self.logger_system.log(LogLevel.ERROR, ComponentType.FACE_RECOGNITION,
#                                    f"Stream error: {str(e)}")
#             self.error_occurred.emit(f"Stream error: {str(e)}")
#
#     def stop_recognition(self):
#         """Stop the face recognition process"""
#         self.mutex.lock()
#         self.running = False
#         self.mutex.unlock()
#
#         # Clean up camera resources
#         self.camera_manager.release_camera_resources()
#         self.logger_system.log(LogLevel.INFO, ComponentType.FACE_RECOGNITION,
#                                "Face recognition stopped and camera resources released")
#
#
# # Configuration
# RPI_HOST = find_raspberry_pi_ip()
# PORT = 5002
# RPI_USER = "sakhtar"
# RPI_PASSWORD = "raspberry"
# SERVER_SCRIPT = "server.py"
#
#
# class StatusCard(QFrame):
#     def __init__(self, title, value="--", unit="", icon=""):
#         super().__init__()
#         self.setFixedSize(180, 100)
#         self.setStyleSheet("""
#             QFrame {
#                 background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
#                     stop:0 rgba(255, 255, 255, 0.1), stop:1 rgba(255, 255, 255, 0.05));
#                 border: 1px solid rgba(255, 255, 255, 0.2);
#                 border-radius: 15px;
#                 backdrop-filter: blur(10px);
#             }
#         """)
#
#         layout = QVBoxLayout(self)
#         layout.setContentsMargins(15, 10, 15, 10)
#         layout.setSpacing(5)
#
#         title_label = QLabel(f"{icon} {title}")
#         title_label.setFont(QFont("Segoe UI", 9))
#         title_label.setStyleSheet("color: rgba(255, 255, 255, 0.8);")
#
#         self.value_label = QLabel(f"{value} {unit}")
#         self.value_label.setFont(QFont("Segoe UI", 16, QFont.Bold))
#         self.value_label.setStyleSheet("color: #00E676;")
#         self.value_label.setAlignment(Qt.AlignCenter)
#
#         layout.addWidget(title_label)
#         layout.addWidget(self.value_label)
#
#     def update_value(self, value, unit="", color="#00E676"):
#         self.value_label.setText(f"{value} {unit}")
#         self.value_label.setStyleSheet(f"color: {color};")
#
#
# class ModernButton(QPushButton):
#     """Modern styled button with gradient and hover effects"""
#
#     def __init__(self, text, icon="", color="#2196F3"):
#         super().__init__(f"{icon} {text}")
#         self.setMinimumHeight(50)
#         self.setFont(QFont("Segoe UI", 11, QFont.Bold))
#         self.default_color = color
#         self.setStyleSheet(self.get_style(color))
#
#     def get_style(self, color):
#         return f"""
#             QPushButton {{
#                 background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
#                     stop:0 {color}, stop:1 {self.darken_color(color, 0.8)});
#                 color: white;
#                 border: none;
#                 border-radius: 12px;
#                 padding: 8px 16px;
#                 font-weight: bold;
#                 text-align: center;
#             }}
#             QPushButton:hover {{
#                 background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
#                     stop:0 {self.darken_color(color, 1.2)}, stop:1 {self.darken_color(color, 0.9)});
#             }}
#             QPushButton:pressed {{
#                 background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
#                     stop:0 {self.darken_color(color, 0.7)}, stop:1 {self.darken_color(color, 0.6)});
#             }}
#             QPushButton:disabled {{
#                 background: #666666;
#                 color: #999999;
#             }}
#         """
#
#     def darken_color(self, color, factor):
#         color = color.lstrip('#')
#         rgb = tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))
#         rgb = tuple(int(c * factor) for c in rgb)
#         rgb = tuple(min(255, max(0, c)) for c in rgb)
#         return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
#
#     def set_enabled_state(self, enabled):
#         self.setEnabled(enabled)
#
#
# class ServerConnectionThread(QThread):
#     """Thread for handling server connections with enhanced logging"""
#     status_update = pyqtSignal(str, str)  # message, color
#     connection_ready = pyqtSignal(bool)
#
#     def __init__(self, action="check", logger_system: HexapodLogger = None):
#         super().__init__()
#         self.action = action
#         self.logger_system = logger_system
#
#     def run(self):
#         try:
#             if self.action == "connect":
#                 self.connect_and_start_server()
#             elif self.action == "check":
#                 self.check_server_status()
#         except Exception as e:
#             if self.logger_system:
#                 self.logger_system.log(LogLevel.ERROR, ComponentType.SERVER_CONNECTION,
#                                        f"Connection thread error: {str(e)}")
#             self.status_update.emit(f"❌ Error: {str(e)}", "#F44336")
#
#     def connect_ssh(self):
#         try:
#             ssh = paramiko.SSHClient()
#             ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
#             ssh.connect(RPI_HOST, username=RPI_USER, password=RPI_PASSWORD, timeout=10)
#             return ssh
#         except Exception as e:
#             if self.logger_system:
#                 self.logger_system.log(LogLevel.ERROR, ComponentType.SERVER_CONNECTION,
#                                        f"SSH connection failed: {str(e)}")
#             self.status_update.emit(f"❌ SSH Failed: {str(e)}", "#F44336")
#             return None
#
#     def connect_and_start_server(self):
#         self.status_update.emit("🔄 Connecting to Raspberry Pi...", "#FFC107")
#
#         if self.logger_system:
#             self.logger_system.log(LogLevel.INFO, ComponentType.SERVER_CONNECTION, "Starting server connection process")
#
#         ssh = self.connect_ssh()
#         if not ssh:
#             return
#
#         try:
#             # Check if server is already running
#             self.status_update.emit("🔍 Checking server status...", "#FFC107")
#             stdin, stdout, stderr = ssh.exec_command("pgrep -f server.py")
#             running_process = stdout.read().decode().strip()
#
#             if not running_process:
#                 # Start the server - COMPLETE THE COMMAND
#                 self.status_update.emit("🚀 Starting Hexapod server...", "#FFC107")
#                 command = (
#                     "source /home/sakhtar/Freenove_Big_Hexapod_Robot_Kit_for_Raspberry_Pi/Code/Sazid/HexapodGUI/myenv/bin/activate && "
#                     "nohup python /home/sakhtar/Freenove_Big_Hexapod_Robot_Kit_for_Raspberry_Pi/Code/Sazid/HexapodGUI/server.py > server.log 2>&1 &"
#                 )
#
#                 # Execute the command
#                 stdin, stdout, stderr = ssh.exec_command(command)
#
#                 # Wait a moment for the server to start
#                 time.sleep(3)
#
#                 # Verify server started successfully
#                 stdin, stdout, stderr = ssh.exec_command("pgrep -f server.py")
#                 new_process = stdout.read().decode().strip()
#
#                 if new_process:
#                     self.status_update.emit("✅ Server started successfully", "#4CAF50")
#                     if self.logger_system:
#                         self.logger_system.log(LogLevel.INFO, ComponentType.SERVER_CONNECTION,
#                                                f"Server started with PID: {new_process}")
#                     self.connection_ready.emit(True)
#                 else:
#                     # Check for startup errors
#                     stdin, stdout, stderr = ssh.exec_command("tail -n 5 server.log 2>/dev/null || echo 'No log file'")
#                     error_log = stdout.read().decode().strip()
#
#                     self.status_update.emit("❌ Server failed to start", "#F44336")
#                     if self.logger_system:
#                         self.logger_system.log(LogLevel.ERROR, ComponentType.SERVER_CONNECTION,
#                                                f"Server startup failed. Log: {error_log}")
#                     self.connection_ready.emit(False)
#             else:
#                 # Server is already running
#                 self.status_update.emit("✅ Server already running", "#4CAF50")
#                 if self.logger_system:
#                     self.logger_system.log(LogLevel.INFO, ComponentType.SERVER_CONNECTION,
#                                            f"Server already running with PID: {running_process}")
#                 self.connection_ready.emit(True)
#
#             # Test server connectivity
#             self.status_update.emit("🔗 Testing server connection...", "#FFC107")
#             if self.test_server_connection():
#                 self.status_update.emit("✅ Server ready for commands", "#4CAF50")
#                 if self.logger_system:
#                     self.logger_system.log(LogLevel.INFO, ComponentType.SERVER_CONNECTION,
#                                            "Server connection test successful")
#             else:
#                 self.status_update.emit("⚠️ Server running but not responding", "#FF9800")
#                 if self.logger_system:
#                     self.logger_system.log(LogLevel.WARNING, ComponentType.SERVER_CONNECTION,
#                                            "Server not responding to connection test")
#
#         except paramiko.AuthenticationException as e:
#             error_msg = f"Authentication failed: {str(e)}"
#             self.status_update.emit(f"❌ {error_msg}", "#F44336")
#             if self.logger_system:
#                 self.logger_system.log(LogLevel.ERROR, ComponentType.SERVER_CONNECTION, error_msg)
#             self.connection_ready.emit(False)
#
#         except paramiko.SSHException as e:
#             error_msg = f"SSH connection error: {str(e)}"
#             self.status_update.emit(f"❌ {error_msg}", "#F44336")
#             if self.logger_system:
#                 self.logger_system.log(LogLevel.ERROR, ComponentType.SERVER_CONNECTION, error_msg)
#             self.connection_ready.emit(False)
#
#         except socket.timeout:
#             error_msg = "Connection timed out"
#             self.status_update.emit(f"❌ {error_msg}", "#F44336")
#             if self.logger_system:
#                 self.logger_system.log(LogLevel.ERROR, ComponentType.SERVER_CONNECTION, error_msg)
#             self.connection_ready.emit(False)
#
#         except socket.gaierror as e:
#             error_msg = f"Network error - cannot resolve host: {str(e)}"
#             self.status_update.emit(f"❌ {error_msg}", "#F44336")
#             if self.logger_system:
#                 self.logger_system.log(LogLevel.ERROR, ComponentType.SERVER_CONNECTION, error_msg)
#             self.connection_ready.emit(False)
#
#         except Exception as e:
#             error_msg = f"Unexpected error: {str(e)}"
#             self.status_update.emit(f"❌ {error_msg}", "#F44336")
#             if self.logger_system:
#                 self.logger_system.log(LogLevel.ERROR, ComponentType.SERVER_CONNECTION,
#                                        f"Unexpected error in server connection: {str(e)}")
#             self.connection_ready.emit(False)
#
#         finally:
#             # Always close SSH connection
#             try:
#                 if ssh:
#                     ssh.close()
#                     if self.logger_system:
#                         self.logger_system.log(LogLevel.DEBUG, ComponentType.SERVER_CONNECTION, "SSH connection closed")
#             except Exception as e:
#                 if self.logger_system:
#                     self.logger_system.log(LogLevel.WARNING, ComponentType.SERVER_CONNECTION,
#                                            f"Error closing SSH connection: {str(e)}")
#
#
# # 5. Add proper directory checking
# def ensure_directories():
#     """Ensuring required directories exist"""
#     directories = ["hexapod_logs", "known_images"]
#     for directory in directories:
#         os.makedirs(directory, exist_ok=True)
#
#
# # 6. Improve error handling for camera operations
# def release_camera_resources(self) -> bool:
#     """Release all camera-related processes on Raspberry Pi"""
#     try:
#         with self.camera_lock:
#             ssh = paramiko.SSHClient()
#             ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
#
#             try:
#                 ssh.connect(self.rpi_host, username=self.rpi_user,
#                             password=self.rpi_password, timeout=10)
#             except Exception as e:
#                 self.logger.error(f"SSH connection failed: {e}")
#                 return False
#
#             # Commands to kill camera processes - remove sudo if not available
#             kill_commands = [
#                 "pkill -f libcamera || true",
#                 "pkill -f raspistill || true",
#                 "pkill -f raspivid || true",
#                 "pkill -f video_server.py || true",
#                 "pkill -f video_stream_server.py || true",
#                 "pkill -f 'python.*8000' || true",
#                 "pkill -f 'python.*camera' || true",
#                 "fuser -k /dev/video0 2>/dev/null || true"
#             ]
#
#             for cmd in kill_commands:
#                 try:
#                     stdin, stdout, stderr = ssh.exec_command(cmd)
#                     stdout.read()  # Wait for command completion
#                     self.logger.info(f"Executed: {cmd}")
#                 except Exception as e:
#                     self.logger.warning(f"Command failed: {cmd} - {e}")
#
#             ssh.close()
#             time.sleep(2)
#
#             self.logger.info("Camera resources released successfully")
#             return True
#
#     except Exception as e:
#         self.logger.error(f"Failed to release camera resources: {e}")
#         return False
#
#
# # main execution guard and initialization
# class MainWindow(QMainWindow):
#     def __init__(self, logger_system):
#         super().__init__()
#         self.logger_system = logger_system
#         self.setWindowTitle("Hexapod Control")
#         self.setGeometry(100, 100, 800, 600)
#         self.init_ui()
#
#     def init_ui(self):
#         label = QLabel("Hexapod GUI is running", self)
#         label.setAlignment(Qt.AlignCenter)
#         self.setCentralWidget(label)
#
#
# if __name__ == "__main__":
#     # Ensure required directories exist
#     ensure_directories()
#
#     # Initialize logging system
#     logger_system = HexapodLogger()
#
#     # Check dependencies
#     missing_deps = []
#     if not DEEPFACE_AVAILABLE:
#         missing_deps.append("deepface")
#     if not TTS_AVAILABLE:
#         missing_deps.append("pyttsx3")
#
#     if missing_deps:
#         print(f"Warning: Missing dependencies: {', '.join(missing_deps)}")
#         print("Install with: pip install " + " ".join(missing_deps))
#
#     # Start Qt application
#     app = QApplication(sys.argv)
#
#     # Create and show main window
#     window = MainWindow(logger_system)
#     window.show()
#
#     # Execute application
#     sys.exit(app.exec_())


import threading
import time
import sys
import socket
import json
import cv2
import os
import csv
import datetime
import pyttsx3
import paramiko
import subprocess
import numpy as np
from deepface import DeepFace

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect, QThread, pyqtSignal, QMutex, QObject
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QLabel,
                             QVBoxLayout, QHBoxLayout, QWidget, QFrame, QGridLayout,
                             QGroupBox, QProgressBar, QTextEdit, QSlider, QSplashScreen)
from PyQt5.QtGui import QImage, QPixmap, QFont, QPalette, QLinearGradient, QBrush, QColor

# Initialize TTS engine
tts_engine = pyttsx3.init()
tts_engine.setProperty('rate', 150)
tts_engine.setProperty('volume', 1.0)


def speak_offline(message):
    tts_engine.say(message)
    tts_engine.runAndWait()


def get_pi_ip():
    try:
        return socket.gethostbyname("raspberrypi.local")
    except socket.gaierror:
        return "192.168.1.173"  # Fallback IP


def find_raspberry_pi_ip():
    try:
        hostname = "raspberrypi.local"
        ip_address = socket.gethostbyname(hostname)
        return ip_address
    except socket.gaierror:
        return get_pi_ip()


class FaceRecognitionWorker(QObject):
    """Worker class for face recognition that runs in a separate QThread"""
    frame_processed = pyqtSignal(np.ndarray)  # Signal to send processed frames
    recognition_result = pyqtSignal(str, tuple)  # Signal for recognition results
    error_occurred = pyqtSignal(str)  # Signal for errors

    def __init__(self, rpi_host):
        super().__init__()
        self.rpi_host = rpi_host
        self.running = False
        self.mutex = QMutex()

    def start_recognition(self):
        """Start the face recognition process"""
        self.mutex.lock()
        self.running = True
        self.mutex.unlock()

        try:
            stream_url = f"http://{self.rpi_host}:8000/video_feed"
            cap = cv2.VideoCapture(stream_url)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

            frame_count = 0
            recognition_interval = 30
            last_result = ("Unknown", (0, 0, 255))

            while self.running and cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    time.sleep(0.1)
                    continue

                # Resize frame for better performance
                height, width = frame.shape[:2]
                if width > 640:
                    scale_factor = 640 / width
                    new_width = int(width * scale_factor)
                    new_height = int(height * scale_factor)
                    frame = cv2.resize(frame, (new_width, new_height))

                frame_count += 1

                # Face detection (fast operation)
                try:
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    faces = face_cascade.detectMultiScale(
                        gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
                    )

                    # Only run recognition periodically and if faces detected
                    if frame_count % recognition_interval == 0 and len(faces) > 0:
                        try:
                            result = DeepFace.find(
                                img_path=frame,
                                db_path="known_images",
                                model_name="Facenet",
                                enforce_detection=False,
                                distance_metric="cosine",
                                threshold=0.7,
                                silent=True
                            )

                            if len(result) > 0 and not result[0].empty:
                                identity_path = result[0].iloc[0]['identity']
                                filename = os.path.basename(identity_path)
                                label = os.path.splitext(filename)[0]
                                last_result = (label, (0, 255, 0))

                                # Emit recognition result
                                self.recognition_result.emit(label, (0, 255, 0))

                                # Log recognition
                                try:
                                    with open("recognition_log.csv", mode="a", newline='') as file:
                                        writer = csv.writer(file)
                                        writer.writerow([datetime.datetime.now(), "person1", label])
                                except:
                                    pass
                            else:
                                last_result = ("Unknown", (0, 0, 255))

                        except Exception as e:
                            self.error_occurred.emit(f"Recognition error: {str(e)}")
                            last_result = ("Error", (255, 0, 0))

                    # Draw face rectangles with last known result
                    label, color = last_result
                    for (x, y, w, h) in faces:
                        cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                        cv2.putText(frame, label, (x, y - 10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

                    # Add processing indicator
                    if frame_count % recognition_interval < 5:
                        cv2.putText(frame, "Processing...", (10, 30),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

                    # Emit processed frame
                    self.frame_processed.emit(frame)

                except Exception as e:
                    self.error_occurred.emit(f"Frame processing error: {str(e)}")

                # Control frame rate
                time.sleep(0.033)  # ~30 FPS

            cap.release()

        except Exception as e:
            self.error_occurred.emit(f"Stream error: {str(e)}")

    def stop_recognition(self):
        """Stop the face recognition process"""
        self.mutex.lock()
        self.running = False
        self.mutex.unlock()


RPI_HOST = find_raspberry_pi_ip()
PORT = 5002
RPI_USER = "sakhtar"
RPI_PASSWORD = "raspberry"
SERVER_SCRIPT = "server.py"
status_update = pyqtSignal(str, str)  # message, color
connection_ready = pyqtSignal(bool)


def __init__(self, action="check"):
    super().__init__()
    self.action = action


def run(self):
    try:
        if self.action == "connect":
            self.connect_and_start_server()
        elif self.action == "check":
            self.check_server_status()
    except Exception as e:
        self.status_update.emit(f"❌ Error: {str(e)}", "#F44336")


def connect_ssh(self):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(RPI_HOST, username=RPI_USER, password=RPI_PASSWORD, timeout=10)
        return ssh
    except Exception as e:
        self.status_update.emit(f"❌ SSH Failed: {str(e)}", "#F44336")
        return None


def connect_and_start_server(self):
    self.status_update.emit("🔄 Connecting to Raspberry Pi...", "#FFC107")

    ssh = self.connect_ssh()
    if not ssh:
        return

    try:
        # Check if server is already running
        self.status_update.emit("🔍 Checking server status...", "#FFC107")
        stdin, stdout, stderr = ssh.exec_command("pgrep -f server.py")
        running_process = stdout.read().decode().strip()

        if not running_process:
            # Start the server
            self.status_update.emit("🚀 Starting Hexapod server...", "#FFC107")
            command = (
                "source /home/sakhtar/Freenove_Big_Hexapod_Robot_Kit_for_Raspberry_Pi/Code/Sazid/HexapodGUI/myenv/bin/activate && "
                "nohup python /home/sakhtar/Freenove_Big_Hexapod_Robot_Kit_for_Raspberry_Pi/Code/Sazid/HexapodGUI/server.py > server.log 2>&1 &"
            )
            ssh.exec_command(command)
            time.sleep(3)  # Wait for server to start

        # Test connection to server
        self.status_update.emit("🧪 Testing server connection...", "#FFC107")
        test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        test_socket.settimeout(5)
        test_socket.connect((RPI_HOST, PORT))
        test_socket.close()

        self.status_update.emit("✅ Connected & Ready!", "#4CAF50")
        self.connection_ready.emit(True)

    except Exception as e:
        self.status_update.emit(f"❌ Connection failed: {str(e)}", "#F44336")
        self.connection_ready.emit(False)
    finally:
        ssh.close()


def check_server_status(self):
    try:
        test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        test_socket.settimeout(3)
        test_socket.connect((RPI_HOST, PORT))
        test_socket.close()
        self.status_update.emit("✅ Server Online", "#4CAF50")
        self.connection_ready.emit(True)
    except:
        self.status_update.emit("🔴 Server Offline", "#F44336")
        self.connection_ready.emit(False)


class ServerConnectionThread(QThread):
    def __init__(self, text, icon="", color="#2196F3"):
        super().__init__(f"{icon} {text}")
        self.setMinimumHeight(50)
        self.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.default_color = color
        self.setStyleSheet(self.get_style(color))

    def get_style(self, color):
        return f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {color}, stop:1 {self.darken_color(color, 0.8)});
                color: white;
                border: none;
                border-radius: 12px;
                padding: 8px 16px;
                font-weight: bold;
                text-align: center;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.darken_color(color, 1.2)}, stop:1 {self.darken_color(color, 0.9)});
            }}
            QPushButton:pressed {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.darken_color(color, 0.7)}, stop:1 {self.darken_color(color, 0.6)});
            }}
            QPushButton:disabled {{
                background: #666666;
                color: #999999;
            }}
        """

    def darken_color(self, color, factor):
        color = color.lstrip('#')
        rgb = tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))
        rgb = tuple(int(c * factor) for c in rgb)
        rgb = tuple(min(255, max(0, c)) for c in rgb)
        return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"

    def set_enabled_state(self, enabled):
        self.setEnabled(enabled)


class StatusCard(QFrame):
    def __init__(self, title, value="--", unit="", icon=""):
        super().__init__()
        self.setFixedSize(180, 100)
        self.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(255, 255, 255, 0.1), stop:1 rgba(255, 255, 255, 0.05));
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 15px;
                backdrop-filter: blur(10px);
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(5)

        title_label = QLabel(f"{icon} {title}")
        title_label.setFont(QFont("Segoe UI", 9))
        title_label.setStyleSheet("color: rgba(255, 255, 255, 0.8);")

        self.value_label = QLabel(f"{value} {unit}")
        self.value_label.setFont(QFont("Segoe UI", 16, QFont.Bold))
        self.value_label.setStyleSheet("color: #00E676;")
        self.value_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(title_label)
        layout.addWidget(self.value_label)

    def update_value(self, value, unit="", color="#00E676"):
        self.value_label.setText(f"{value} {unit}")
        self.value_label.setStyleSheet(f"color: {color};")


class HexapodGUI(QMainWindow):
    def __init__(self):
        super(HexapodGUI, self).__init__()
        self.recognition_running = False
        self.video_streaming = False
        self.server_connected = False
        self.connection_thread = None

        # Face recognition components
        self.recognition_thread = None
        self.recognition_worker = None

        self.init_ui()

        # Auto-check server status on startup
        self.check_server_status()

    def init_ui(self):
        self.setWindowTitle("🕷️ HEXAPOD Command Center v2.0")
        self.setGeometry(100, 100, 1300, 850)

        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #0f0f23, stop:0.5 #1a1a2e, stop:1 #16213e);
            }
            QGroupBox {
                font: bold 12px "Segoe UI";
                color: white;
                border: 2px solid rgba(255, 255, 255, 0.2);
                border-radius: 10px;
                margin-top: 10px;
                padding-top: 10px;
                background: rgba(255, 255, 255, 0.05);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #00BCD4;
            }
            QLabel {
                color: white;
                font: 11px "Segoe UI";
            }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Left panel - Controls
        left_panel = self.create_control_panel()
        main_layout.addWidget(left_panel, 1)

        # Right panel - Video and status
        right_panel = self.create_video_panel()
        main_layout.addWidget(right_panel, 2)

    def create_control_panel(self):
        panel = QWidget()
        panel.setMaximumWidth(420)
        layout = QVBoxLayout(panel)
        layout.setSpacing(15)

        # Header
        header = QLabel("🤖 HEXAPOD CONTROL CENTER")
        header.setFont(QFont("Segoe UI", 18, QFont.Bold))
        header.setStyleSheet("""
            color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #00BCD4, stop:1 #2196F3);
            padding: 10px;
            border-bottom: 2px solid rgba(255, 255, 255, 0.2);
            margin-bottom: 10px;
        """)
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)

        # Connection Panel
        connection_group = QGroupBox("🔗 Server Connection")
        connection_layout = QVBoxLayout(connection_group)

        # Connection status display
        self.connection_status = QLabel("🔄 Checking connection...")
        self.connection_status.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.connection_status.setStyleSheet("""
            background: rgba(255, 193, 7, 0.2);
            border: 1px solid #FFC107;
            border-radius: 8px;
            padding: 12px;
            color: #FFC107;
        """)
        self.connection_status.setAlignment(Qt.AlignCenter)
        connection_layout.addWidget(self.connection_status)

        # Connection buttons
        conn_btn_layout = QHBoxLayout()
        self.connect_btn = ModernButton("One-Click Connect", "🚀", "#4CAF50")
        self.disconnect_btn = ModernButton("Disconnect", "🔌", "#F44336")
        self.refresh_btn = ModernButton("Refresh", "🔄", "#FF9800")

        self.connect_btn.clicked.connect(self.one_click_connect)
        self.disconnect_btn.clicked.connect(self.disconnect_server)
        self.refresh_btn.clicked.connect(self.check_server_status)

        conn_btn_layout.addWidget(self.connect_btn)
        conn_btn_layout.addWidget(self.refresh_btn)
        connection_layout.addLayout(conn_btn_layout)
        connection_layout.addWidget(self.disconnect_btn)

        layout.addWidget(connection_group)

        # Movement controls
        movement_group = QGroupBox("🎮 Movement Controls")
        movement_layout = QGridLayout(movement_group)
        movement_layout.setSpacing(10)

        self.forward_btn = ModernButton("Forward", "⬆️", "#4CAF50")
        self.backward_btn = ModernButton("Backward", "⬇️", "#FF5722")
        self.left_btn = ModernButton("Left", "⬅️", "#2196F3")
        self.right_btn = ModernButton("Right", "➡️", "#FF9800")

        # Disable movement buttons initially
        for btn in [self.forward_btn, self.backward_btn, self.left_btn, self.right_btn]:
            btn.set_enabled_state(False)

        movement_layout.addWidget(self.forward_btn, 0, 1)
        movement_layout.addWidget(self.left_btn, 1, 0)
        movement_layout.addWidget(self.right_btn, 1, 2)
        movement_layout.addWidget(self.backward_btn, 2, 1)

        self.forward_btn.clicked.connect(lambda: (self.send_command("forward"), speak_offline("Moving forward")))
        self.backward_btn.clicked.connect(lambda: (self.send_command("backward"), speak_offline("Moving backward")))
        self.left_btn.clicked.connect(lambda: (self.send_command("left"), speak_offline("Turning left")))
        self.right_btn.clicked.connect(lambda: (self.send_command("right"), speak_offline("Turning right")))

        layout.addWidget(movement_group)

        # Sensor controls
        sensor_group = QGroupBox("📊 Sensors & Status")
        sensor_layout = QVBoxLayout(sensor_group)

        cards_layout = QHBoxLayout()
        self.distance_card = StatusCard("Distance", "--", "cm", "📏")
        self.battery_card = StatusCard("Battery", "--", "V", "🔋")
        cards_layout.addWidget(self.distance_card)
        cards_layout.addWidget(self.battery_card)
        sensor_layout.addLayout(cards_layout)

        sensor_btn_layout = QHBoxLayout()
        self.distance_btn = ModernButton("Distance", "📏", "#9C27B0")
        self.battery_btn = ModernButton("Battery", "🔋", "#FF5722")
        self.distance_btn.set_enabled_state(False)
        self.battery_btn.set_enabled_state(False)

        self.distance_btn.clicked.connect(lambda: self.send_command("distance"))
        self.battery_btn.clicked.connect(lambda: self.send_command("battery_level"))

        sensor_btn_layout.addWidget(self.distance_btn)
        sensor_btn_layout.addWidget(self.battery_btn)
        sensor_layout.addLayout(sensor_btn_layout)

        layout.addWidget(sensor_group)

        # Action controls
        action_group = QGroupBox("🎬 Actions")
        action_layout = QVBoxLayout(action_group)

        action_btn_layout1 = QHBoxLayout()
        self.buzzer_btn = ModernButton("Buzzer", "🔊", "#E91E63")
        self.capture_btn = ModernButton("Capture", "📸", "#00BCD4")
        self.buzzer_btn.set_enabled_state(False)
        self.capture_btn.set_enabled_state(False)

        self.buzzer_btn.clicked.connect(self.test_buzzer)
        self.capture_btn.clicked.connect(self.capture_photo)

        action_btn_layout1.addWidget(self.buzzer_btn)
        action_btn_layout1.addWidget(self.capture_btn)
        action_layout.addLayout(action_btn_layout1)

        action_btn_layout2 = QHBoxLayout()
        self.video_btn = ModernButton("Start Video", "📹", "#607D8B")
        self.recognition_btn = ModernButton("Face Recognition", "🧠", "#795548")
        self.video_btn.set_enabled_state(False)
        self.recognition_btn.set_enabled_state(False)

        self.video_btn.clicked.connect(self.toggle_video_stream)
        self.recognition_btn.clicked.connect(self.toggle_face_recognition)

        action_btn_layout2.addWidget(self.video_btn)
        action_btn_layout2.addWidget(self.recognition_btn)
        action_layout.addLayout(action_btn_layout2)

        layout.addWidget(action_group)

        # System controls
        system_group = QGroupBox("⚙️ System")
        system_layout = QVBoxLayout(system_group)

        system_btn_layout = QHBoxLayout()
        self.restart_server_btn = ModernButton("Restart Server", "🔄", "#FF9800")
        self.exit_btn = ModernButton("Exit", "🚪", "#F44336")

        self.restart_server_btn.clicked.connect(self.restart_server)
        self.exit_btn.clicked.connect(self.close)

        system_btn_layout.addWidget(self.restart_server_btn)
        system_btn_layout.addWidget(self.exit_btn)
        system_layout.addLayout(system_btn_layout)

        layout.addWidget(system_group)

        layout.addStretch()
        return panel

    def create_video_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(15)

        # Video display area
        video_group = QGroupBox("📺 Live Video Feed")
        video_layout = QVBoxLayout(video_group)

        self.video_label = QLabel()
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setStyleSheet("""
            QLabel {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1a1a1a, stop:1 #2d2d2d);
                border: 2px solid rgba(255, 255, 255, 0.1);
                border-radius: 10px;
            }
        """)
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setText("📺\nVideo Feed\nConnect to server first")
        video_layout.addWidget(self.video_label)

        layout.addWidget(video_group)

        # Activity log
        log_group = QGroupBox("📝 Activity Log")
        log_layout = QVBoxLayout(log_group)

        self.activity_log = QTextEdit()
        self.activity_log.setMaximumHeight(150)
        self.activity_log.setStyleSheet("""
            QTextEdit {
                background: rgba(0, 0, 0, 0.5);
                color: #00E676;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 5px;
                padding: 10px;
                font-family: 'Consolas', monospace;
                font-size: 10px;
            }
        """)
        self.activity_log.setReadOnly(True)
        log_layout.addWidget(self.activity_log)

        layout.addWidget(log_group)

        return panel

    def log_activity(self, message):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.activity_log.append(f"[{timestamp}] {message}")
        scrollbar = self.activity_log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def one_click_connect(self):
        """One-click connection to start server and establish connection"""
        if self.connection_thread and self.connection_thread.isRunning():
            return

        self.connect_btn.set_enabled_state(False)
        self.connection_thread = ServerConnectionThread("connect")
        self.connection_thread.status_update.connect(self.update_connection_status)
        self.connection_thread.connection_ready.connect(self.on_connection_ready)
        self.connection_thread.finished.connect(lambda: self.connect_btn.set_enabled_state(True))
        self.connection_thread.start()
        self.log_activity("🚀 Starting one-click connection...")

    def check_server_status(self):
        """Check if server is already running"""
        if self.connection_thread and self.connection_thread.isRunning():
            return

        self.connection_thread = ServerConnectionThread("check")
        self.connection_thread.status_update.connect(self.update_connection_status)
        self.connection_thread.connection_ready.connect(self.on_connection_ready)
        self.connection_thread.start()

    def update_connection_status(self, message, color):
        """Update connection status display"""
        self.connection_status.setText(message)
        self.connection_status.setStyleSheet(f"""
            background: rgba({self.hex_to_rgb(color)}, 0.2);
            border: 1px solid {color};
            border-radius: 8px;
            padding: 12px;
            color: {color};
            font-weight: bold;
        """)
        self.log_activity(message)

    def hex_to_rgb(self, hex_color):
        """Convert hex color to RGB string"""
        hex_color = hex_color.lstrip('#')
        return ', '.join(str(int(hex_color[i:i + 2], 16)) for i in (0, 2, 4))

    def on_connection_ready(self, ready):
        """Enable/disable controls based on connection status"""
        self.server_connected = ready

        # Enable/disable all control buttons
        control_buttons = [
            self.forward_btn, self.backward_btn, self.left_btn, self.right_btn,
            self.distance_btn, self.battery_btn, self.buzzer_btn, self.capture_btn,
            self.video_btn, self.recognition_btn
        ]

        for btn in control_buttons:
            btn.set_enabled_state(ready)

        if ready:
            self.video_label.setText("📺\nVideo Feed\nClick 'Start Video' to begin")
        else:
            self.video_label.setText("📺\nVideo Feed\nConnect to server first")

    def disconnect_server(self):
        """Disconnect from server and stop all activities"""
        try:
            # Stop video and recognition
            self.stop_video_stream()
            self.stop_face_recognition()

            # Stop server via SSH
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(RPI_HOST, username=RPI_USER, password=RPI_PASSWORD, timeout=5)
            ssh.exec_command(f"pkill -f {SERVER_SCRIPT}")
            ssh.close()

            self.server_connected = False
            self.on_connection_ready(False)
            self.update_connection_status("🔌 Disconnected", "#F44336")

        except Exception as e:
            self.log_activity(f"❌ Disconnect error: {str(e)}")

    def restart_server(self):
        """Restart the server"""
        self.log_activity("🔄 Restarting server...")
        self.disconnect_server()
        time.sleep(2)
        self.one_click_connect()

    def send_command(self, command):
        if not self.server_connected:
            self.log_activity("❌ Not connected to server")
            return

        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(5)
            client_socket.connect((RPI_HOST, PORT))

            message = json.dumps({"command": command})
            client_socket.sendall(message.encode())

            response_data = client_socket.recv(1024).decode()
            client_socket.close()

            if response_data:
                response = json.loads(response_data)
                self.handle_response(response, command)

        except Exception as e:
            self.log_activity(f"❌ Command failed: {command} - {str(e)}")

    def handle_response(self, response, command):
        if "distance" in response:
            distance = response["distance"]
            if distance != -1:
                self.distance_card.update_value(f"{distance}", "cm", "#00E676")
                self.log_activity(f"📏 Distance: {distance} cm")
            else:
                self.distance_card.update_value("Error", "", "#F44336")

        if "battery_level" in response:
            battery = response["battery_level"]
            try:
                voltage = float(battery.replace('V', '').strip())
                self.battery_card.update_value(f"{voltage:.2f}", "V", "#00E676")
                self.log_activity(f"🔋 Battery: {voltage:.2f}V")
            except:
                self.battery_card.update_value("Error", "", "#F44336")

        if "buzzer" in response:
            self.log_activity("🔊 Buzzer activated")

        if "image" in response:
            self.log_activity("📸 Photo captured")

        self.log_activity(f"✅ Command: {command}")

    def test_buzzer(self):
        self.send_command("buzzer")

    def capture_photo(self):
        self.send_command("capture")

    def toggle_video_stream(self):
        if not self.video_streaming:
            self.start_video_stream()
        else:
            self.stop_video_stream()

    def start_video_stream(self):
        try:
            self.start_video_server_on_pi()
            time.sleep(2)

            def stream_video():
                url = f"http://{RPI_HOST}:8000/video_feed"
                cap = cv2.VideoCapture(url)

                while cap.isOpened() and self.video_streaming:
                    ret, frame = cap.read()
                    if ret:
                        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        h, w, ch = rgb_frame.shape
                        bytes_per_line = ch * w
                        qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
                        pixmap = QPixmap.fromImage(qt_image).scaled(
                            self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        self.video_label.setPixmap(pixmap)
                    else:
                        break

                cap.release()

            self.video_streaming = True
            self.video_btn.setText("📹 Stop Video")
            threading.Thread(target=stream_video, daemon=True).start()
            self.log_activity("📹 Video stream started")

        except Exception as e:
            self.log_activity(f"❌ Video failed: {str(e)}")

    def stop_video_stream(self):
        self.video_streaming = False
        self.video_btn.setText("📹 Start Video")
        self.video_label.clear()
        self.video_label.setText("📺\nVideo Feed\nClick 'Start Video' to begin")
        self.stop_video_server_on_pi()
        self.log_activity("🛑 Video stopped")

    def toggle_face_recognition(self):
        if not self.recognition_running:
            self.start_face_recognition()
        else:
            self.stop_face_recognition()

    def start_face_recognition(self):
        """Start face recognition with proper Qt threading"""
        try:
            if not os.path.exists("known_images"):
                self.log_activity("❌ 'known_images' folder not found!")
                return

            # Count images in known_images folder
            image_count = len([f for f in os.listdir("known_images")
                               if f.lower().endswith(('.png', '.jpg', '.jpeg'))])

            if image_count == 0:
                self.log_activity("❌ No reference images found in 'known_images' folder!")
                return

            self.log_activity(f"📸 Found {image_count} reference images")

            # Start video server
            self.start_video_server_on_pi()
            time.sleep(3)

            # Initialize CSV log
            try:
                with open("recognition_log.csv", mode="w", newline='') as file:
                    writer = csv.writer(file)
                    writer.writerow(["timestamp", "ground_truth", "predicted"])
            except Exception as e:
                self.log_activity(f"⚠️ Could not create log file: {str(e)}")

            # Create worker and thread
            self.recognition_worker = FaceRecognitionWorker(RPI_HOST)
            self.recognition_thread = QThread()

            # Move worker to thread
            self.recognition_worker.moveToThread(self.recognition_thread)

            # Connect signals
            self.recognition_worker.frame_processed.connect(self.update_recognition_frame)
            self.recognition_worker.recognition_result.connect(self.handle_recognition_result)
            self.recognition_worker.error_occurred.connect(self.handle_recognition_error)

            # Connect thread signals
            self.recognition_thread.started.connect(self.recognition_worker.start_recognition)
            self.recognition_thread.finished.connect(self.recognition_worker.deleteLater)

            # Start the thread
            self.recognition_thread.start()

            self.recognition_running = True
            self.recognition_btn.setText("🧠 Stop Recognition")
            self.recognition_btn.setStyleSheet(self.recognition_btn.get_style("#F44336"))

            self.log_activity("🧠 Face recognition started (Qt threading)")

        except Exception as e:
            self.log_activity(f"❌ Face recognition failed: {str(e)}")
            self.recognition_running = False

    def update_recognition_frame(self, frame):
        """Update GUI with processed frame - runs in main thread"""
        try:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_frame.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)

            if not qt_image.isNull():
                pixmap = QPixmap.fromImage(qt_image).scaled(
                    self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.video_label.setPixmap(pixmap)

        except Exception as e:
            self.log_activity(f"⚠️ Display update error: {str(e)}")

    def handle_recognition_result(self, label, color):
        """Handle recognition result - runs in main thread"""
        self.log_activity(f"👤 Recognized: {label}")

        # Use QTimer for safe TTS execution
        QTimer.singleShot(100, lambda: self.speak_recognition_result(label))

    def speak_recognition_result(self, label):
        """Safely speak recognition result"""
        try:
            # Run TTS in a separate thread to prevent blocking
            threading.Thread(
                target=speak_offline,
                args=(f"Hello {label}",),
                daemon=True
            ).start()
        except Exception as e:
            self.log_activity(f"⚠️ TTS error: {str(e)}")

    def handle_recognition_error(self, error_msg):
        """Handle recognition errors - runs in main thread"""
        self.log_activity(f"⚠️ {error_msg}")

    def stop_face_recognition(self):
        """Safely stop face recognition"""
        self.recognition_running = False

        if self.recognition_worker:
            self.recognition_worker.stop_recognition()

        if self.recognition_thread and self.recognition_thread.isRunning():
            self.recognition_thread.quit()
            self.recognition_thread.wait(3000)  # Wait up to 3 seconds

        self.recognition_btn.setText("🧠 Face Recognition")
        self.recognition_btn.setStyleSheet(self.recognition_btn.get_style(self.recognition_btn.default_color))

        self.log_activity("🛑 Face recognition stopped")

        # Clean up
        self.recognition_worker = None
        self.recognition_thread = None

    def stop_face_recognition(self):
        """Safely stop face recognition"""
        self.recognition_running = False

        if self.recognition_worker:
            self.recognition_worker.stop_recognition()

        if self.recognition_thread and self.recognition_thread.isRunning():
            self.recognition_thread.quit()
            self.recognition_thread.wait(3000)  # Wait up to 3 seconds

        self.recognition_btn.setText("🧠 Face Recognition")
        self.recognition_btn.setStyleSheet(self.recognition_btn.get_style(self.recognition_btn.default_color))

        self.log_activity("🛑 Face recognition stopped")

        # Clean up
        self.recognition_worker = None
        self.recognition_thread = None

    def closeEvent(self, event):
        """Handle application closing"""
        try:
            # Stop all activities
            self.recognition_running = False
            self.video_streaming = False

            # Stop face recognition properly
            if self.recognition_worker:
                self.recognition_worker.stop_recognition()

            if self.recognition_thread and self.recognition_thread.isRunning():
                self.recognition_thread.quit()
                self.recognition_thread.wait(2000)

            # Stop video server
            self.stop_video_server_on_pi()

            # Stop connection thread if running
            if self.connection_thread and self.connection_thread.isRunning():
                self.connection_thread.quit()
                self.connection_thread.wait(2000)

        except Exception as e:
            print(f"Cleanup error: {str(e)}")

        event.accept()

    def start_video_server_on_pi(self):
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(RPI_HOST, username=RPI_USER, password=RPI_PASSWORD, timeout=5)

            # Check if already running
            stdin, stdout, stderr = ssh.exec_command("pgrep -f video_server.py")
            if stdout.read().decode().strip():
                ssh.close()
                return

            # Start video server
            command = (
                "source /home/sakhtar/Freenove_Big_Hexapod_Robot_Kit_for_Raspberry_Pi/Code/Sazid/HexapodGUI/myenv/bin/activate && "
                "nohup python /home/sakhtar/Freenove_Big_Hexapod_Robot_Kit_for_Raspberry_Pi/Code/Sazid/HexapodGUI/video_stream_server.py > video.log 2>&1 &"
            )
            ssh.exec_command(command)
            ssh.close()

        except Exception as e:
            self.log_activity(f"❌ Failed to start video server: {str(e)}")

    def stop_video_server_on_pi(self):
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(RPI_HOST, username=RPI_USER, password=RPI_PASSWORD, timeout=5)
            ssh.exec_command("pkill -f video_server.py")
            ssh.close()

        except Exception as e:
            self.log_activity(f"❌ Failed to stop video server: {str(e)}")


class SplashScreen(QSplashScreen):
    def __init__(self):
        super().__init__()
        self.setFixedSize(400, 300)

        # Create gradient background
        pixmap = QPixmap(400, 300)
        pixmap.fill(Qt.transparent)

        painter = QtGui.QPainter(pixmap)
        gradient = QLinearGradient(0, 0, 400, 300)
        gradient.setColorAt(0, QColor("#0f0f23"))
        gradient.setColorAt(0.5, QColor("#1a1a2e"))
        gradient.setColorAt(1, QColor("#16213e"))

        painter.fillRect(0, 0, 400, 300, QBrush(gradient))

        # Add text
        painter.setPen(QColor("white"))
        painter.setFont(QFont("Segoe UI", 20, QFont.Bold))
        painter.drawText(50, 150, "🕷️ HEXAPOD")
        painter.setFont(QFont("Segoe UI", 12))
        painter.drawText(100, 180, "Command Center v2.0")
        painter.drawText(120, 220, "Loading...")

        painter.end()
        self.setPixmap(pixmap)


def main():
    app = QApplication(sys.argv)

    # Show splash screen
    splash = SplashScreen()
    splash.show()
    app.processEvents()

    # Simulate loading time
    time.sleep(2)

    # Create and show main window
    window = HexapodGUI()
    window.show()

    # Close splash screen
    splash.close()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()