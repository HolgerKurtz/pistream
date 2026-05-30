import os
from dotenv import load_dotenv

load_dotenv()


def get_config() -> dict:
    return {
        'camera_index':     int(os.getenv('CAMERA_INDEX', 1)),
        'web_port':         int(os.getenv('WEB_PORT', 5001)),
        'bg_history':       int(os.getenv('BG_HISTORY', 500)),
        'bg_var_threshold': float(os.getenv('BG_VAR_THRESHOLD', 4.0)),
        'min_area':         int(os.getenv('BIRD_MIN_AREA', 10)),
        'max_area':         int(os.getenv('BIRD_MAX_AREA', 50000)),
        'max_brightness':   int(os.getenv('BIRD_MAX_BRIGHTNESS', 120)),
        'trail_length':     int(os.getenv('TRAIL_LENGTH', 60)),
        'trail_thickness':  int(os.getenv('TRAIL_THICKNESS', 3)),
        'max_disappeared':  int(os.getenv('MAX_DISAPPEARED', 10)),
        'warmup_frames':    int(os.getenv('WARMUP_FRAMES', 60)),
        'min_track_age':    int(os.getenv('MIN_TRACK_AGE', 2)),
        'flip_horizontal':      os.getenv('FLIP_HORIZONTAL', 'false').lower() == 'true',
        'display_quality':      int(os.getenv('DISPLAY_QUALITY', 85)),
        'recalibrate_interval':  float(os.getenv('RECALIBRATE_INTERVAL', 15.0)),
        'sky_darkness_pct':      int(os.getenv('SKY_DARKNESS_PCT', 25)),
        'max_match_distance':    int(os.getenv('MAX_MATCH_DISTANCE', 150)),
    }
