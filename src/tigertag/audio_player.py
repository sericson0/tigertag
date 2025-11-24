# Audio playback imports
import pygame

class AudioPlayer:
    """Audio player with play/pause/stop controls using pygame."""
    
    def __init__(self):
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        self.current_file = None
        self.is_playing = False
        self.is_paused = False
    
    def load(self, file_path: Path):
        """Load an audio file."""
        try:
            pygame.mixer.music.load(str(file_path))
            self.current_file = file_path
            return True
        except Exception as e:
            print(f"Error loading audio: {e}")
            return False
    
    def play(self):
        """Start or resume playback."""
        if self.is_paused:
            pygame.mixer.music.unpause()
            self.is_paused = False
        else:
            pygame.mixer.music.play()
        self.is_playing = True
    
    def pause(self):
        """Pause playback."""
        pygame.mixer.music.pause()
        self.is_paused = True
        self.is_playing = False
    
    def stop(self):
        """Stop playback."""
        pygame.mixer.music.stop()
        self.is_playing = False
        self.is_paused = False
    
    def get_busy(self):
        """Check if audio is currently playing."""
        return pygame.mixer.music.get_busy()
    
    def set_volume(self, volume: float):
        """Set volume (0.0 to 1.0)."""
        pygame.mixer.music.set_volume(volume)
    
    def cleanup(self):
        """Clean up pygame resources."""
        pygame.mixer.quit()


# Global player instance
_player = AudioPlayer()


def play_audio(file_path: Path, preview_duration: int = 30):
    """
    Play audio file with optional preview duration.
    
    Parameters:
    -----------
    file_path : Path
        Path to audio file
    preview_duration : int
        Seconds to play (0 = full song)
    """
    global _player
    
    if _player.load(file_path):
        _player.play()
        print(f"♪ Playing: {file_path.name}")
        
        if preview_duration > 0:
            print(f"  (Preview: {preview_duration}s - Press Ctrl+C to stop early)")
            try:
                time.sleep(preview_duration)
                _player.stop()
                print("  Preview ended")
            except KeyboardInterrupt:
                _player.stop()
                print("\n  Stopped by user")


def pause_audio():
    """Pause current playback."""
    _player.pause()
    print("♪ Paused")


def resume_audio():
    """Resume paused playback."""
    _player.play()
    print("♪ Resumed")


def stop_audio():
    """Stop current playback."""
    _player.stop()
    print("♪ Stopped")


def is_playing():
    """Check if audio is currently playing."""
    return _player.get_busy()


def cleanup_audio():
    """Call this when done tagging to clean up resources."""
    global _player
    _player.cleanup()