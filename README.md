```
fire_detection_system/
│
├── .env                    # Environment variables
├── .gitignore             # Git ignore file
├── requirements.txt       # Project dependencies
│
├── src/                   # Source code directory
│   ├── __init__.py
│   ├── config.py          # Configuration and environment setup
│   ├── fire_detector.py   # Fire detection logic
│   ├── notification_service.py  # WhatsApp and Imgur services
│   └── main.py           # Application entry point
│
├── models/               # Model directory
│   └── best.pt          # YOLO model file
│
├── data/                # Data directory
│   └── vid.mp4         # Input video file
│
├── logs/               # Logging directory
│   └── fire_detection.log
│
├── tests/              # Test directory
│   ├── __init__.py
│   ├── test_fire_detector.py
│   └── test_notification_service.py
│
└── detected_fires/     # Directory for saving detected fire images
    └── README.md       # Explanation of directory purpose
```