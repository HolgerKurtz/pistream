import pygame
import numpy as np
import logging
import time

logger = logging.getLogger(__name__)

class MusicGenerator:
    def __init__(self):
        """Initialize the MusicGenerator with pygame.mixer for direct audio."""
        try:
            # Initialize mixer with CD quality audio
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            logger.info("MusicGenerator (Audio) initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize pygame.mixer: {e}")
            self.output = None
            return

        # State to track previous notes
        self.last_note_left = None
        self.last_note_right = None
        
        # Pentatonic scale (MIDI numbers)
        # C4, D4, E4, G4, A4, C5, ...
        self.scale_midi = [60, 62, 64, 67, 69, 72, 74, 76, 79, 81, 84, 86, 88, 91, 93, 96]
        
        # Pre-generate sounds
        self.sounds = {}
        self._generate_sounds()
        
    def _generate_sounds(self):
        """Generate sine wave sounds for each note in the scale."""
        logger.info("Generating synthesized sounds...")
        sample_rate = 44100
        duration = 0.5  # seconds
        
        # Time array
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        
        for note in self.scale_midi:
            # Calculate frequency
            frequency = 440.0 * (2.0 ** ((note - 69.0) / 12.0))
            
            # Generate sine wave
            wave = np.sin(2 * np.pi * frequency * t)
            
            # Apply envelope (decay) to make it sound like a pluck
            envelope = np.exp(-3 * t)
            wave = wave * envelope
            
            # Normalize to 16-bit range (-32767 to 32767)
            # Stereo: duplicate for left/right
            audio = np.zeros((len(wave), 2), dtype=np.int16)
            max_val = 32767 // 2 # Headroom
            audio[:, 0] = (wave * max_val).astype(np.int16)
            audio[:, 1] = (wave * max_val).astype(np.int16)
            
            # Create pygame Sound object
            self.sounds[note] = pygame.sndarray.make_sound(audio)
            
        logger.info(f"Generated {len(self.sounds)} sounds.")

    def _map_y_to_note(self, y_norm):
        """
        Map normalized Y coordinate (0.0 top to 1.0 bottom) to a note in the scale.
        """
        # Invert Y because 0 is top (high pitch) and 1 is bottom (low pitch)
        val = 1.0 - y_norm
        val = max(0.0, min(1.0, val))
        
        # Map to index in scale
        idx = int(val * (len(self.scale_midi) - 1))
        return self.scale_midi[idx]

    def process_pose(self, keypoints):
        """
        Process pose keypoints to generate music.
        """
        if not pygame.mixer.get_init():
            return

        if not hasattr(keypoints, 'xyn') or len(keypoints.xyn) == 0:
            return

        person_keypoints = keypoints.xyn[0]
        confs = keypoints.conf[0] if keypoints.conf is not None else None
        conf_thresh = 0.5

        # Process Left Hand (Wrist index 9)
        if confs is None or confs[9] > conf_thresh:
            left_wrist = person_keypoints[9]
            if left_wrist[0] != 0 and left_wrist[1] != 0:
                note = self._map_y_to_note(float(left_wrist[1]))
                if note != self.last_note_left:
                    self.sounds[note].play()
                    self.last_note_left = note
        else:
            self.last_note_left = None

        # Process Right Hand (Wrist index 10)
        if confs is None or confs[10] > conf_thresh:
            right_wrist = person_keypoints[10]
            if right_wrist[0] != 0 and right_wrist[1] != 0:
                note = self._map_y_to_note(float(right_wrist[1]))
                if note != self.last_note_right:
                    self.sounds[note].play()
                    self.last_note_right = note
        else:
            self.last_note_right = None

    def close(self):
        """Clean up resources."""
        pygame.mixer.quit()
        logger.info("MusicGenerator closed.")
