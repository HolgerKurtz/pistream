import os
from dotenv import load_dotenv

load_dotenv()


def get_config() -> dict:
    return {
        'host':             os.getenv('PI_IP', 'localhost'),
        'port':             int(os.getenv('PORT', 5555)),
        'web_port':         int(os.getenv('WEB_PORT', 5001)),
        'bg_history':       int(os.getenv('BG_HISTORY', 500)),
        'bg_var_threshold': float(os.getenv('BG_VAR_THRESHOLD', 16.0)),
        'min_area':         int(os.getenv('BIRD_MIN_AREA', 20)),
        'max_area':         int(os.getenv('BIRD_MAX_AREA', 2000)),
        'trail_length':     int(os.getenv('TRAIL_LENGTH', 60)),
        'max_disappeared':  int(os.getenv('MAX_DISAPPEARED', 10)),
        'warmup_frames':    int(os.getenv('WARMUP_FRAMES', 60)),
        'min_track_age':    int(os.getenv('MIN_TRACK_AGE', 4)),
        'flip_horizontal':  os.getenv('FLIP_HORIZONTAL', 'true').lower() == 'true',
        'stream_width':     int(os.getenv('STREAM_WIDTH', 1280)),
        'stream_height':    int(os.getenv('STREAM_HEIGHT', 720)),
        'stream_quality':   int(os.getenv('STREAM_QUALITY', 85)),
        'display_quality':  int(os.getenv('DISPLAY_QUALITY', 85)),
    }
