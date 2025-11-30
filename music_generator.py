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
        
        # Pentatonic scale (MIDI numbers)
        self.scale_midi = [60, 62, 64, 67, 69, 72, 74, 76, 79, 81, 84, 86, 88, 91, 93, 96]
        
        # Durations (decay factors)
        self.decay_factors = [1.0, 3.0, 5.0, 8.0, 15.0] 
        
        # Sound banks: [decay_index][note] -> Sound
        self.sound_banks = []
        self._generate_sounds()
        
    def _generate_sounds(self):
        """Generate rich synthesized sounds (additive synthesis) for each note."""
        logger.info("Generating synthesized sounds with harmonics...")
        sample_rate = 44100
        max_duration = 2.0  # seconds buffer size
        
        # Time array
        t = np.linspace(0, max_duration, int(sample_rate * max_duration), False)
        
        for decay in self.decay_factors:
            bank = {}
            for note in self.scale_midi:
                # Fundamental frequency
                f0 = 440.0 * (2.0 ** ((note - 69.0) / 12.0))
                
                # Additive Synthesis: Fundamental + Harmonics
                # Amplitudes for harmonics (1st, 2nd, 3rd, etc.)
                # This creates a more "piano/organ" like timbre
                harmonics = [
                    (1.0, 1.0),   # Fundamental
                    (2.0, 0.5),   # 2nd harmonic (octave)
                    (3.0, 0.25),  # 3rd harmonic (fifth)
                    (4.0, 0.125), # 4th harmonic
                    (5.0, 0.06)   # 5th harmonic
                ]
                
                wave = np.zeros_like(t)
                
                for mult, amp in harmonics:
                    wave += amp * np.sin(2 * np.pi * (f0 * mult) * t)
                
                # Normalize wave before envelope
                wave = wave / np.max(np.abs(wave))
                
                # Apply envelope (decay)
                envelope = np.exp(-decay * t)
                wave = wave * envelope
                
                # Normalize to 16-bit range (-32767 to 32767)
                audio = np.zeros((len(wave), 2), dtype=np.int16)
                max_val = 32767 // 2 
                audio[:, 0] = (wave * max_val).astype(np.int16)
                audio[:, 1] = (wave * max_val).astype(np.int16)
                
                # Create pygame Sound object
                bank[note] = pygame.sndarray.make_sound(audio)
            
            self.sound_banks.append(bank)
            
        logger.info(f"Generated {len(self.sound_banks)} sound banks.")

    def _map_y_to_note(self, y_norm):
        """Map normalized Y coordinate to a note in the scale."""
        val = 1.0 - y_norm
        val = max(0.0, min(1.0, val))
        idx = int(val * (len(self.scale_midi) - 1))
        return self.scale_midi[idx]

    def _map_y_to_duration_index(self, y_norm):
        """Map normalized Y coordinate to a duration index."""
        val = y_norm # 0 is top
        val = max(0.0, min(1.0, val))
        idx = int(val * (len(self.decay_factors) - 1))
        return idx

    def process_pose(self, keypoints):
        """
        Process pose keypoints.
        Left Hand: Pitch (triggers note).
        Right Hand: Duration (selects bank).
        """
        if not pygame.mixer.get_init():
            return

        if not hasattr(keypoints, 'xyn') or len(keypoints.xyn) == 0:
            return

        person_keypoints = keypoints.xyn[0]
        confs = keypoints.conf[0] if keypoints.conf is not None else None
        conf_thresh = 0.5

        # Determine Duration from Right Hand (Wrist index 10)
        duration_idx = 2 # Default to medium
        if confs is not None and confs[10] > conf_thresh:
            right_wrist = person_keypoints[10]
            if right_wrist[0] != 0 and right_wrist[1] != 0:
                duration_idx = self._map_y_to_duration_index(float(right_wrist[1]))

        # Process Left Hand (Wrist index 9) for Note Trigger
        if confs is None or confs[9] > conf_thresh:
            left_wrist = person_keypoints[9]
            if left_wrist[0] != 0 and left_wrist[1] != 0:
                note = self._map_y_to_note(float(left_wrist[1]))
                
                # Only play if note changed
                if note != self.last_note_left:
                    # Play sound from the selected bank
                    self.sound_banks[duration_idx][note].play()
                    self.last_note_left = note
        else:
            self.last_note_left = None

    def close(self):
        """Clean up resources."""
        pygame.mixer.quit()
        logger.info("MusicGenerator closed.")
