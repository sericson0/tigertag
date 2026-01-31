#!/usr/bin/env python3
"""
Batch Audio Processor
Converts audio files to:
- 48kHz sample rate
- 24-bit depth
- Mono channel
- AUFS (Average Unit Full Scale) normalization
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from pydub import AudioSegment
import numpy as np
from typing import List, Optional, Dict
try:
    from mutagen import File as MutagenFile
    from mutagen.id3 import ID3NoHeaderError
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False


def check_ffprobe_available() -> bool:
    """
    Check if FFprobe is available in the system PATH.
    
    Returns:
        True if FFprobe is available, False otherwise
    """
    try:
        result = subprocess.run(
            ['ffprobe', '-version'],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return False


def extract_metadata_ffmpeg(input_path: Path) -> Dict[str, str]:
    """
    Extract metadata from audio file using FFprobe.
    
    Args:
        input_path: Path to input audio file
    
    Returns:
        Dictionary of metadata tags
    """
    metadata = {}
    if not check_ffprobe_available():
        return metadata
    
    try:
        # Use FFprobe to extract metadata as JSON
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            str(input_path)
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0,
            timeout=10
        )
        
        if result.returncode == 0:
            try:
                data = json.loads(result.stdout, strict=False)
                if 'format' in data and 'tags' in data['format']:
                    tags = data['format']['tags']
                    # Map common tag names
                    tag_mapping = {
                        'title': 'title',
                        'TITLE': 'title',
                        'artist': 'artist',
                        'ARTIST': 'artist',
                        'album': 'album',
                        'ALBUM': 'album',
                        'album_artist': 'albumartist',
                        'ALBUMARTIST': 'albumartist',
                        'date': 'date',
                        'DATE': 'date',
                        'year': 'date',
                        'YEAR': 'date',
                        'genre': 'genre',
                        'GENRE': 'genre',
                        'track': 'tracknumber',
                        'TRACK': 'tracknumber',
                        'TRACKNUMBER': 'tracknumber',
                        'disc': 'discnumber',
                        'DISC': 'discnumber',
                        'DISCNUMBER': 'discnumber',
                        'composer': 'composer',
                        'COMPOSER': 'composer',
                        'comment': 'comment',
                        'COMMENT': 'comment',
                    }
                    
                    for key, value in tags.items():
                        normalized_key = tag_mapping.get(key.lower(), key.lower())
                        if value:
                            # Ensure UTF-8 encoding is preserved
                            if isinstance(value, bytes):
                                value = value.decode('utf-8', errors='replace')
                            elif not isinstance(value, str):
                                value = str(value)
                            # Store as UTF-8 string
                            metadata[normalized_key] = value
            except (json.JSONDecodeError, UnicodeDecodeError, KeyError):
                pass
    except (FileNotFoundError, json.JSONDecodeError, subprocess.TimeoutExpired, Exception):
        pass
    
    return metadata


def extract_metadata_mutagen(input_path: Path) -> Dict[str, str]:
    """
    Extract metadata from audio file using mutagen library.
    
    Args:
        input_path: Path to input audio file
    
    Returns:
        Dictionary of metadata tags
    """
    metadata = {}
    if not MUTAGEN_AVAILABLE:
        return metadata
    
    try:
        audio_file = MutagenFile(str(input_path))
        if audio_file is None:
            return metadata
        
        # Common tag mappings
        tag_mapping = {
            'TIT2': 'title',      # ID3v2
            'TITLE': 'title',      # Vorbis, APE
            'TPE1': 'artist',      # ID3v2
            'ARTIST': 'artist',    # Vorbis, APE
            'TALB': 'album',       # ID3v2
            'ALBUM': 'album',      # Vorbis, APE
            'TPE2': 'albumartist', # ID3v2
            'ALBUMARTIST': 'albumartist',  # Vorbis
            'TDRC': 'date',        # ID3v2
            'TDAT': 'date',        # ID3v2
            'DATE': 'date',        # Vorbis, APE
            'TCON': 'genre',       # ID3v2
            'GENRE': 'genre',      # Vorbis, APE
            'TRCK': 'tracknumber', # ID3v2
            'TRACKNUMBER': 'tracknumber',  # Vorbis, APE
            'TPOS': 'discnumber',  # ID3v2
            'DISCNUMBER': 'discnumber',     # Vorbis
            'TCOM': 'composer',    # ID3v2
            'COMPOSER': 'composer', # Vorbis, APE
            'COMM': 'comment',     # ID3v2
            'COMMENT': 'comment',  # Vorbis, APE
        }
        
        for tag_key, normalized_key in tag_mapping.items():
            if tag_key in audio_file:
                value = audio_file[tag_key]
                if isinstance(value, list) and len(value) > 0:
                    metadata[normalized_key] = str(value[0])
                elif value:
                    metadata[normalized_key] = str(value)
        
        # Also try to get all tags generically
        for key in audio_file.keys():
            if key not in tag_mapping:
                try:
                    value = audio_file[key]
                    if isinstance(value, list) and len(value) > 0:
                        metadata[key.lower()] = str(value[0])
                    elif value:
                        metadata[key.lower()] = str(value)
                except:
                    pass
                    
    except Exception:
        pass
    
    return metadata


def extract_album_art(input_path: Path) -> Optional[bytes]:
    """
    Extract album art/cover image from audio file.
    
    Args:
        input_path: Path to input audio file
    
    Returns:
        Album art image data as bytes, or None if not found
    """
    if not MUTAGEN_AVAILABLE:
        return None
    
    try:
        audio_file = MutagenFile(str(input_path))
        if audio_file is None:
            return None
        
        file_ext = input_path.suffix.lower()
        
        if file_ext == '.mp3':
            # MP3 uses APIC frames in ID3 tags
            from mutagen.id3 import APIC
            if 'APIC:' in audio_file:
                apic = audio_file['APIC:'].data
                return apic
        elif file_ext in ['.flac', '.ogg']:
            # FLAC/OGG use PICTURE blocks in Vorbis comments
            if hasattr(audio_file, 'pictures') and audio_file.pictures:
                return audio_file.pictures[0].data
            # Also try metadata key
            for key in audio_file.keys():
                if 'PICTURE' in key.upper() or 'COVER' in key.upper():
                    try:
                        pic_data = audio_file[key]
                        if isinstance(pic_data, list) and len(pic_data) > 0:
                            if hasattr(pic_data[0], 'data'):
                                return pic_data[0].data
                            elif isinstance(pic_data[0], bytes):
                                return pic_data[0]
                    except:
                        pass
        elif file_ext in ['.m4a', '.mp4']:
            # M4A/MP4 use covr atoms
            if 'covr' in audio_file:
                covr = audio_file['covr']
                if isinstance(covr, list) and len(covr) > 0:
                    return covr[0]
    except Exception:
        pass
    
    return None


def apply_album_art(output_path: Path, album_art: bytes) -> bool:
    """
    Apply album art/cover image to output file.
    
    Args:
        output_path: Path to output audio file
        album_art: Album art image data as bytes
    
    Returns:
        True if successful, False otherwise
    """
    if not MUTAGEN_AVAILABLE or not album_art:
        return False
    
    try:
        audio_file = MutagenFile(str(output_path))
        if audio_file is None:
            return False
        
        file_ext = output_path.suffix.lower()
        
        if file_ext == '.mp3':
            # MP3 uses APIC frames
            from mutagen.id3 import ID3, APIC, ID3NoHeaderError
            try:
                tags = ID3(str(output_path))
            except ID3NoHeaderError:
                tags = ID3()
            
            # Determine MIME type from image data
            mime_type = 'image/jpeg'
            if album_art.startswith(b'\x89PNG'):
                mime_type = 'image/png'
            elif album_art.startswith(b'GIF'):
                mime_type = 'image/gif'
            
            tags['APIC'] = APIC(
                encoding=3,
                mime=mime_type,
                type=3,  # Cover (front)
                desc='Cover',
                data=album_art
            )
            tags.save(str(output_path))
            return True
            
        elif file_ext in ['.flac', '.ogg']:
            # FLAC/OGG use PICTURE blocks
            from mutagen.flac import Picture
            picture = Picture()
            picture.type = 3  # Cover (front)
            picture.mime = 'image/jpeg'
            if album_art.startswith(b'\x89PNG'):
                picture.mime = 'image/png'
            elif album_art.startswith(b'GIF'):
                picture.mime = 'image/gif'
            picture.data = album_art
            audio_file.add_picture(picture)
            audio_file.save()
            return True
            
        elif file_ext in ['.m4a', '.mp4']:
            # M4A/MP4 use covr atoms
            audio_file['covr'] = [album_art]
            audio_file.save()
            return True
            
    except Exception:
        pass
    
    return False


def extract_metadata(input_path: Path) -> Dict[str, str]:
    """
    Extract metadata from audio file using available methods.
    
    Args:
        input_path: Path to input audio file
    
    Returns:
        Dictionary of metadata tags
    """
    # Try FFprobe first (most reliable)
    metadata = extract_metadata_ffmpeg(input_path)
    
    # Fallback to mutagen if FFprobe didn't work or returned empty
    if not metadata and MUTAGEN_AVAILABLE:
        metadata = extract_metadata_mutagen(input_path)
    
    return metadata


def apply_metadata_ffmpeg(input_path: Path, output_path: Path, metadata: Dict[str, str]) -> bool:
    """
    Apply metadata to output file using FFmpeg.
    
    Args:
        input_path: Path to input audio file (for copying metadata)
        output_path: Path to output audio file
        metadata: Dictionary of metadata tags to apply
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # First, try to copy all metadata from input file using map_metadata
        # This preserves all metadata including cover art, custom tags, etc.
        # Only try this if input_path exists and is different from output_path
        if input_path.exists() and input_path != output_path:
            temp_output = Path(str(output_path) + '.meta.tmp')
            
            cmd = [
                'ffmpeg',
                '-i', str(output_path),
                '-i', str(input_path),
                '-map', '0:a',  # Map audio from first input (output file)
                '-map', '1:t?',  # Map all attachments (cover art, etc.) from input file if they exist
                '-map_metadata', '1',  # Copy all metadata from second input (input file)
                '-c:a', 'copy',  # Copy audio without re-encoding
                '-c:v', 'copy',  # Copy any video/attachments without re-encoding
                '-y',
                str(temp_output)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0,
                timeout=30
            )
            
            if result.returncode == 0 and temp_output.exists():
                # Replace original with metadata-enhanced file
                try:
                    temp_output.replace(output_path)
                    return True
                except Exception as e:
                    # If replace fails, try to copy and then delete temp
                    try:
                        import shutil
                        shutil.copy2(temp_output, output_path)
                        temp_output.unlink()
                        return True
                    except:
                        pass
        
        # If copying failed or input_path doesn't exist, try setting metadata explicitly
        if metadata:
            temp_output = Path(str(output_path) + '.meta.tmp')
            cmd = [
                'ffmpeg',
                '-i', str(output_path),
            ]
            
            # Add metadata parameters with proper UTF-8 encoding
            for key, value in metadata.items():
                # Ensure value is a UTF-8 string
                if isinstance(value, bytes):
                    value = value.decode('utf-8', errors='replace')
                elif not isinstance(value, str):
                    value = str(value)
                
                # Escape special characters in metadata values for FFmpeg
                # FFmpeg uses : as separator, so we need to escape it
                escaped_value = str(value).replace('\\', '\\\\').replace(':', '\\:').replace('=', '\\=')
                cmd.extend(['-metadata', f'{key}={escaped_value}'])
            
            cmd.extend([
                '-c:a', 'copy',  # Copy audio without re-encoding
                '-y',
                str(temp_output)
            ])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0,
                timeout=30
            )
            
            if result.returncode == 0 and temp_output.exists():
                try:
                    temp_output.replace(output_path)
                    return True
                except Exception as e:
                    # If replace fails, try to copy and then delete temp
                    try:
                        import shutil
                        shutil.copy2(temp_output, output_path)
                        temp_output.unlink()
                        return True
                    except Exception as e2:
                        # Clean up temp file
                        try:
                            if temp_output.exists():
                                temp_output.unlink()
                        except:
                            pass
                        # Log error but don't fail completely
                        print(f"  - Warning: Could not replace output file with metadata: {str(e2)}")
            
            # Log error if metadata setting failed, but don't print full error if it's just a warning
            if result.returncode != 0:
                # Check if it's a non-critical error (like "already exists" warnings)
                stderr_lower = result.stderr.lower() if result.stderr else ""
                if "already exists" in stderr_lower or "overwrite" in stderr_lower:
                    # This is usually just a warning, try to use the file anyway
                    if temp_output.exists():
                        try:
                            temp_output.replace(output_path)
                            return True
                        except:
                            pass
                # Don't print error here - will fall back to mutagen which is more reliable
                # FFmpeg metadata errors are common and mutagen handles them better
                pass
                    
    except Exception:
        pass
    
    return False


def apply_metadata_mutagen(output_path: Path, metadata: Dict[str, str]) -> bool:
    """
    Apply metadata to output file using mutagen library.
    
    Args:
        output_path: Path to output audio file
        metadata: Dictionary of metadata tags to apply
    
    Returns:
        True if successful, False otherwise
    """
    if not MUTAGEN_AVAILABLE or not metadata:
        return False
    
    try:
        audio_file = MutagenFile(str(output_path))
        if audio_file is None:
            return False
        
        # Map normalized keys to format-specific tag names
        file_ext = output_path.suffix.lower()
        
        if file_ext == '.mp3':
            # ID3v2 tags
            from mutagen.id3 import ID3, TIT2, TPE1, TALB, TPE2, TDRC, TCON, TRCK, TPOS, TCOM, COMM
            try:
                tags = ID3(str(output_path))
            except ID3NoHeaderError:
                tags = ID3()
            
            # Helper function to ensure UTF-8 string
            def ensure_utf8(value):
                if isinstance(value, bytes):
                    return value.decode('utf-8', errors='replace')
                return str(value)
            
            if 'title' in metadata:
                tags['TIT2'] = TIT2(encoding=3, text=[ensure_utf8(metadata['title'])])
            if 'artist' in metadata:
                tags['TPE1'] = TPE1(encoding=3, text=[ensure_utf8(metadata['artist'])])
            if 'album' in metadata:
                tags['TALB'] = TALB(encoding=3, text=[ensure_utf8(metadata['album'])])
            if 'albumartist' in metadata:
                tags['TPE2'] = TPE2(encoding=3, text=[ensure_utf8(metadata['albumartist'])])
            if 'date' in metadata:
                tags['TDRC'] = TDRC(encoding=3, text=[ensure_utf8(metadata['date'])])
            if 'genre' in metadata:
                tags['TCON'] = TCON(encoding=3, text=[ensure_utf8(metadata['genre'])])
            if 'tracknumber' in metadata:
                tags['TRCK'] = TRCK(encoding=3, text=[ensure_utf8(metadata['tracknumber'])])
            if 'discnumber' in metadata:
                tags['TPOS'] = TPOS(encoding=3, text=[ensure_utf8(metadata['discnumber'])])
            if 'composer' in metadata:
                tags['TCOM'] = TCOM(encoding=3, text=[ensure_utf8(metadata['composer'])])
            if 'comment' in metadata:
                tags['COMM'] = COMM(encoding=3, text=[ensure_utf8(metadata['comment'])], desc='', lang='eng')
            
            tags.save(str(output_path))
            return True
            
        elif file_ext in ['.flac', '.ogg']:
            # Vorbis comment tags - ensure UTF-8
            for key, value in metadata.items():
                # Ensure UTF-8 encoding
                if isinstance(value, bytes):
                    value = value.decode('utf-8', errors='replace')
                elif not isinstance(value, str):
                    value = str(value)
                audio_file[key.upper()] = [value]  # Vorbis tags are lists
            audio_file.save()
            return True
            
        elif file_ext in ['.m4a', '.mp4']:
            # MP4/iTunes tags - ensure UTF-8
            tag_mapping = {
                'title': '\xa9nam',
                'artist': '\xa9ART',
                'album': '\xa9alb',
                'albumartist': 'aART',
                'date': '\xa9day',
                'genre': '\xa9gen',
                'tracknumber': 'trkn',
                'discnumber': 'disk',
                'composer': '\xa9wrt',
                'comment': '\xa9cmt',
            }
            for key, value in metadata.items():
                # Ensure UTF-8 encoding
                if isinstance(value, bytes):
                    value = value.decode('utf-8', errors='replace')
                elif not isinstance(value, str):
                    value = str(value)
                mp4_key = tag_mapping.get(key.lower(), key)
                audio_file[mp4_key] = [value]  # MP4 tags are lists
            audio_file.save()
            return True
            
        else:
            # Generic tag setting - ensure UTF-8
            for key, value in metadata.items():
                # Ensure UTF-8 encoding
                if isinstance(value, bytes):
                    value = value.decode('utf-8', errors='replace')
                elif not isinstance(value, str):
                    value = str(value)
                audio_file[key] = value
            audio_file.save()
            return True
            
    except Exception:
        return False


def apply_metadata(output_path: Path, input_path: Path, metadata: Dict[str, str]) -> bool:
    """
    Apply metadata to output file using available methods.
    
    Args:
        output_path: Path to output audio file
        input_path: Path to input audio file (for copying metadata, optional)
        metadata: Dictionary of metadata tags to apply
    
    Returns:
        True if successful, False otherwise
    """
    # Try mutagen first (more reliable and doesn't require file operations)
    if MUTAGEN_AVAILABLE:
        if apply_metadata_mutagen(output_path, metadata):
            return True
    
    # Fallback to FFmpeg if mutagen failed (for formats mutagen doesn't support well)
    # Only use FFmpeg if input_path exists and is different from output_path
    if check_ffmpeg_available() and input_path and input_path.exists() and input_path != output_path:
        if apply_metadata_ffmpeg(input_path, output_path, metadata):
            return True
    
    return False


def check_ffmpeg_available() -> bool:
    """
    Check if FFmpeg is available in the system PATH.
    
    Returns:
        True if FFmpeg is available, False otherwise
    """
    try:
        result = subprocess.run(
            ['ffmpeg', '-version'],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        )
        return result.returncode == 0
    except (FileNotFoundError, OSError):
        return False


def aufs_normalize(audio_segment: AudioSegment, target_lufs: float = -13.0) -> AudioSegment:
    """
    Normalize audio using AUFS (Average Unit Full Scale) / LUFS (Loudness Units Full Scale).
    
    Args:
        audio_segment: AudioSegment to normalize
        target_lufs: Target LUFS value (default -13.0)
    
    Returns:
        Normalized AudioSegment
    """
    # Convert to numpy array for processing
    samples = np.array(audio_segment.get_array_of_samples())
    
    # Reshape if stereo
    if audio_segment.channels == 2:
        samples = samples.reshape(-1, 2)
    
    # Calculate RMS (Root Mean Square) for AUFS normalization
    # AUFS uses average RMS level, which is simpler than full LUFS calculation
    # Convert samples to float for accurate calculation
    samples_float = samples.astype(np.float64)
    
    # Normalize samples to [-1, 1] range
    max_amplitude = 2 ** (audio_segment.sample_width * 8 - 1)
    samples_normalized = samples_float / max_amplitude
    
    # Calculate RMS
    rms = np.sqrt(np.mean(samples_normalized ** 2))
    
    # Convert RMS to dB (approximate LUFS for AUFS)
    # AUFS ≈ 20 * log10(RMS)
    current_lufs = 20 * np.log10(rms) if rms > 0 else -np.inf
    
    # Calculate gain needed
    if current_lufs != -np.inf:
        gain_db = target_lufs - current_lufs
        # Apply gain
        audio_segment = audio_segment.apply_gain(gain_db)
    
    return audio_segment


def process_audio_file(
    input_path: Path, 
    output_path: Path, 
    target_lufs: float = -13.0,
    convert_to_flac: bool = False,
    convert_to_mono: bool = False,
    convert_to_48khz: bool = False,
    use_24bit: bool = False,
    normalize: bool = False
) -> bool:
    """
    Process a single audio file with optional transformations.
    
    Args:
        input_path: Path to input audio file
        output_path: Path to output audio file
        target_lufs: Target LUFS for normalization (default: -13.0)
        convert_to_flac: If True, convert AFLAC files to FLAC
        convert_to_mono: If True, convert stereo to mono
        convert_to_48khz: If True, convert sample rate to 48kHz
        use_24bit: If True, export with 24-bit depth
        normalize: If True, normalize audio using AUFS
    
    Returns:
        True if successful, False otherwise
    """
    try:
        print(f"Processing: {input_path.name}")
        
        # Verify input file exists
        if not input_path.exists():
            raise FileNotFoundError(f"Input file does not exist: {input_path}")
        
        # Extract metadata and album art from input file
        metadata = extract_metadata(input_path)
        album_art = extract_album_art(input_path)
        if metadata:
            print(f"  - Extracted metadata: {', '.join(metadata.keys())[:50]}...")
        if album_art:
            print(f"  - Extracted album art ({len(album_art)} bytes)")
        
        # Handle AFLAC to FLAC conversion if requested
        file_ext = input_path.suffix.lower()
        if convert_to_flac and file_ext == '.aflac':
            # Convert AFLAC to FLAC by renaming extension
            # Note: This assumes AFLAC is just FLAC with a different extension
            # If AFLAC is a different format, we'll need to handle it differently
            print(f"  - Converting AFLAC to FLAC")
            file_ext = '.flac'
            # Update output path to use .flac extension
            if output_path.suffix.lower() in ('.aflac', '.flac'):
                output_path = output_path.with_suffix('.flac')
        
        # Check if FFmpeg is required for this file type
        # Most formats (FLAC, MP3, M4A, etc.) require FFmpeg
        formats_requiring_ffmpeg = {'.flac', '.mp3', '.m4a', '.aac', '.ogg', '.wma', '.aiff', '.aflac'}
        
        if file_ext in formats_requiring_ffmpeg and not check_ffmpeg_available():
            raise FileNotFoundError(
                f"FFmpeg is required to process {file_ext} files but was not found in PATH.\n"
                f"Please install FFmpeg and add it to your system PATH.\n"
                f"Download from: https://ffmpeg.org/download.html"
            )
        
        # Load audio file
        try:
            audio = AudioSegment.from_file(str(input_path))
        except FileNotFoundError as e:
            # Check if this is the FFmpeg not found error
            error_str = str(e).lower()
            if 'ffmpeg' in error_str or 'cannot find the file' in error_str:
                raise FileNotFoundError(
                    f"FFmpeg is required to decode {file_ext} files but was not found.\n"
                    f"Please install FFmpeg and add it to your system PATH.\n"
                    f"Download from: https://ffmpeg.org/download.html\n"
                    f"Original error: {str(e)}"
                )
            raise
        except Exception as e:
            raise Exception(f"Failed to load audio file: {str(e)}")
        
        # 1. Convert to mono (if requested)
        if convert_to_mono and audio.channels > 1:
            audio = audio.set_channels(1)
            print(f"  - Converted to mono")
        
        # 2. Convert sample rate to 48kHz (if requested)
        if convert_to_48khz and audio.frame_rate != 48000:
            audio = audio.set_frame_rate(48000)
            print(f"  - Converted sample rate to 48kHz")
        
        # 3. Normalize using AUFS (if requested)
        if normalize:
            audio = aufs_normalize(audio, target_lufs)
            print(f"  - Applied AUFS normalization (target: {target_lufs} LUFS)")
        
        # 4. Export with 24-bit depth
        # Preserve the original file extension
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Get original file extension and preserve it (or use FLAC if converted)
        original_ext = input_path.suffix.lower()
        if convert_to_flac and original_ext == '.aflac':
            original_ext = '.flac'
        if not original_ext:
            original_ext = '.wav'  # Default to wav if no extension
        
        # Ensure output path has the correct extension
        if output_path.suffix.lower() != original_ext:
            output_path = output_path.with_suffix(original_ext)
        
        # Map extension to pydub format name
        format_map = {
            '.mp3': 'mp3',
            '.wav': 'wav',
            '.flac': 'flac',
            '.aac': 'aac',
            '.ogg': 'ogg',
            '.m4a': 'ipod',  # pydub uses 'ipod' for m4a
            '.wma': 'wma',
            '.aiff': 'aiff',
            '.au': 'au'
        }
        output_format = format_map.get(original_ext, 'wav')
        
        # Export as temporary file first (always use wav for temp to ensure compatibility)
        temp_path = output_path.with_suffix('.tmp.wav')
        
        # Ensure we use absolute paths
        temp_path = temp_path.resolve()
        output_path = output_path.resolve()
        
        # Check if FFmpeg is available before trying to use it
        use_ffmpeg = check_ffmpeg_available()
        
        if use_ffmpeg:
            # Export temporary file for FFmpeg processing
            try:
                audio.export(str(temp_path), format='wav')
                
                # Verify temp file was created
                if not temp_path.exists():
                    raise FileNotFoundError(f"Failed to create temporary file: {temp_path}")
                
                # Use ffmpeg to ensure 24-bit depth
                try:
                    # Use absolute paths and ensure they're strings
                    # Build FFmpeg command with format-specific options
                    ffmpeg_cmd = [
                        'ffmpeg',
                        '-i', str(temp_path),
                        '-y',  # Overwrite output file
                    ]
                    
                    # Add sample rate conversion if requested
                    if convert_to_48khz:
                        ffmpeg_cmd.extend(['-ar', '48000'])
                    
                    # Add channel conversion if requested
                    if convert_to_mono:
                        ffmpeg_cmd.extend(['-ac', '1'])
                    
                    # Add format-specific encoding options
                    if original_ext == '.mp3':
                        ffmpeg_cmd.extend(['-codec:a', 'libmp3lame', '-b:a', '320k'])
                    elif original_ext == '.flac':
                        # FLAC doesn't support s24 directly - use s32 (32-bit) which FLAC supports natively
                        # FLAC will encode at 24-bit precision internally
                        if use_24bit:
                            ffmpeg_cmd.extend(['-codec:a', 'flac', '-sample_fmt', 's32', '-compression_level', '12'])
                        else:
                            ffmpeg_cmd.extend(['-codec:a', 'flac', '-compression_level', '12'])
                    elif original_ext == '.m4a' or original_ext == '.aac':
                        ffmpeg_cmd.extend(['-codec:a', 'aac', '-b:a', '320k'])
                    elif original_ext == '.ogg':
                        ffmpeg_cmd.extend(['-codec:a', 'libvorbis', '-q:a', '5'])
                    elif original_ext == '.wma':
                        ffmpeg_cmd.extend(['-codec:a', 'wmav2'])
                    elif original_ext == '.aiff':
                        if use_24bit:
                            ffmpeg_cmd.extend(['-codec:a', 'pcm_s24be'])  # AIFF uses big-endian
                        else:
                            ffmpeg_cmd.extend(['-codec:a', 'pcm_s16be'])  # Default to 16-bit
                    elif original_ext == '.wav':
                        if use_24bit:
                            ffmpeg_cmd.extend(['-codec:a', 'pcm_s24le', '-sample_fmt', 's24'])  # WAV uses little-endian
                        else:
                            ffmpeg_cmd.extend(['-codec:a', 'pcm_s16le'])  # Default to 16-bit
                    else:
                        # Default to WAV encoding for unknown formats
                        if use_24bit:
                            ffmpeg_cmd.extend(['-codec:a', 'pcm_s24le', '-sample_fmt', 's24'])
                        else:
                            ffmpeg_cmd.extend(['-codec:a', 'pcm_s16le'])
                    
                    ffmpeg_cmd.append(str(output_path))
                    
                    result = subprocess.run(
                        ffmpeg_cmd,
                        check=True,
                        capture_output=True,
                        text=True,
                        encoding='utf-8',
                        errors='replace',
                        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
                    )
                    
                    # Remove temporary file
                    if temp_path.exists():
                        try:
                            temp_path.unlink()
                        except:
                            pass
                    if use_24bit:
                        print(f"  - Exported as 24-bit audio using FFmpeg")
                    else:
                        print(f"  - Exported audio using FFmpeg")
                    
                except FileNotFoundError:
                    # FFmpeg not found (shouldn't happen if check passed, but handle anyway)
                    print(f"  - Warning: ffmpeg not found, using pydub export (may not be exactly 24-bit)")
                    audio.export(str(output_path), format=output_format)
                    # Clean up temp file if it exists
                    if temp_path.exists() and temp_path != output_path:
                        try:
                            temp_path.unlink()
                        except:
                            pass
                            
                except subprocess.CalledProcessError as e:
                    # FFmpeg failed - show full error details for debugging
                    error_msg = e.stderr if isinstance(e.stderr, str) else (e.stderr.decode('utf-8', errors='ignore') if e.stderr else str(e))
                    stdout_msg = e.stdout if isinstance(e.stdout, str) else (e.stdout.decode('utf-8', errors='ignore') if e.stdout else '')
                    
                    print(f"  - Warning: FFmpeg failed with return code {e.returncode}")
                    print(f"  - Command: {' '.join(ffmpeg_cmd)}")
                    if error_msg:
                        print(f"  - Error output: {error_msg}")
                    if stdout_msg:
                        print(f"  - Standard output: {stdout_msg[:200]}")
                    print(f"  - Falling back to pydub export (may not be exactly 24-bit)")
                    
                    # Export directly to output
                    audio.export(str(output_path), format=output_format)
                    # Clean up temp file if it exists
                    if temp_path.exists() and temp_path != output_path:
                        try:
                            temp_path.unlink()
                        except:
                            pass
                            
            except Exception as e:
                # If temp file creation fails, fall back to direct export
                print(f"  - Warning: Could not create temp file, using direct export: {str(e)}")
                audio.export(str(output_path), format=output_format)
        else:
            # FFmpeg not available, use pydub export directly
            print(f"  - Note: FFmpeg not found in PATH, using pydub export (may not be exactly 24-bit)")
            audio.export(str(output_path), format=output_format)
        
        # Apply metadata and album art to output file
        if metadata:
            if apply_metadata(output_path, input_path, metadata):
                print(f"  - Metadata preserved")
            else:
                print(f"  - Warning: Could not preserve metadata")
        
        # Apply album art separately (FFmpeg might not preserve it properly)
        if album_art:
            if apply_album_art(output_path, album_art):
                print(f"  - Album art preserved")
            else:
                print(f"  - Warning: Could not preserve album art")
        
        # If we converted AFLAC to FLAC and the original file still exists, delete it
        # Only delete if processing in place (input and output are the same location)
        if convert_to_flac and input_path.suffix.lower() == '.aflac':
            if input_path.exists() and input_path != output_path:
                # Only delete if output is in the same directory (in-place processing)
                if input_path.parent == output_path.parent:
                    try:
                        input_path.unlink()
                        print(f"  - Removed original AFLAC file")
                    except Exception as e:
                        print(f"  - Warning: Could not remove original AFLAC file: {str(e)}")
                else:
                    # Output is in a different location, keep original file
                    print(f"  - Original AFLAC file preserved (output in different folder)")
        
        print(f"  ✓ Successfully processed: {output_path.name}\n")
        return True
        
    except Exception as e:
        print(f"  ✗ Error processing {input_path.name}: {str(e)}\n")
        return False


def find_audio_files(directory: Path) -> List[Path]:
    """
    Find all audio files in a directory.
    
    Args:
        directory: Directory to search
    
    Returns:
        List of unique audio file paths (no duplicates)
    """
    audio_extensions = {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.wma', '.aiff', '.au'}
    # Use a set to track unique files (normalized paths to handle case-insensitive filesystems)
    audio_files_set = set()
    
    for ext in audio_extensions:
        # Search for lowercase extension
        for file_path in directory.rglob(f'*{ext}'):
            # Normalize path to handle case-insensitive filesystems (Windows)
            normalized_path = file_path.resolve()
            audio_files_set.add(normalized_path)
        
        # Search for uppercase extension (but normalize to avoid duplicates)
        for file_path in directory.rglob(f'*{ext.upper()}'):
            normalized_path = file_path.resolve()
            audio_files_set.add(normalized_path)
    
    # Convert set to sorted list (set automatically handles duplicates)
    audio_files = sorted(audio_files_set)
    
    return audio_files


def main():
    """
    Main function to batch process audio files.
    """
    if len(sys.argv) < 2:
        print("Usage: python batch_audio_processor.py <input_directory> [output_directory] [--target-lufs VALUE]")
        print("\nOptions:")
        print("  input_directory    : Directory containing audio files to process")
        print("  output_directory   : Directory to save processed files (default: input_directory/processed)")
        print("  --target-lufs      : Target LUFS value for normalization (default: -13.0)")
        sys.exit(1)
    
    input_dir = Path(sys.argv[1])
    if not input_dir.exists():
        print(f"Error: Input directory '{input_dir}' does not exist.")
        sys.exit(1)
    
    # Parse output directory
    output_dir = None
    target_lufs = -13.0
    
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == '--target-lufs' and i + 1 < len(sys.argv):
            target_lufs = float(sys.argv[i + 1])
            i += 2
        elif output_dir is None:
            output_dir = Path(sys.argv[i])
            i += 1
        else:
            i += 1
    
    if output_dir is None:
        output_dir = input_dir / 'processed'
    
    print(f"Input directory: {input_dir}")
    print(f"Output directory: {output_dir}")
    print(f"Target LUFS: {target_lufs}")
    
    # Check FFmpeg availability
    if not check_ffmpeg_available():
        print("⚠ ERROR: FFmpeg not found in PATH!")
        print("  FFmpeg is REQUIRED to process audio files (especially FLAC, MP3, M4A, etc.)")
        print("  Please install FFmpeg and add it to your system PATH.")
        print("  Download from: https://ffmpeg.org/download.html")
        print("  Or use: choco install ffmpeg (if Chocolatey is installed)")
        print("-" * 60)
        print("Processing will fail for most file formats without FFmpeg.")
        response = input("Continue anyway? (y/n): ").strip().lower()
        if response != 'y':
            print("Aborted.")
            sys.exit(1)
    else:
        print("✓ FFmpeg found")
    
    print("-" * 60)
    
    # Find all audio files
    audio_files = find_audio_files(input_dir)
    
    if not audio_files:
        print("No audio files found in the input directory.")
        sys.exit(1)
    
    print(f"Found {len(audio_files)} unique audio file(s) to process.\n")
    
    # Process each file (track processed files to avoid duplicates)
    successful = 0
    failed = 0
    processed_files = set()  # Track processed files to prevent duplicates
    
    for audio_file in audio_files:
        # Normalize path to handle case-insensitive filesystems
        normalized_input = audio_file.resolve()
        
        # Skip if already processed
        if normalized_input in processed_files:
            print(f"Skipping duplicate: {audio_file.name} (already processed)")
            continue
        
        # Mark as processed
        processed_files.add(normalized_input)
        
        # Calculate relative path to preserve directory structure
        relative_path = audio_file.relative_to(input_dir)
        output_path = output_dir / relative_path
        
        if process_audio_file(audio_file, output_path, target_lufs):
            successful += 1
        else:
            failed += 1
    
    print("-" * 60)
    print(f"Processing complete!")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")
    print(f"  Total: {len(audio_files)}")


if __name__ == '__main__':
    main()

