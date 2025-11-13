 # AIFF uses ID3 tags
def get_id3_text(audio, frame_id: str) -> str:
    frame = audio.tags.get(frame_id)
    return str(frame) if frame else ""


def first(audio, key: str) -> str:
    val = audio.tags.get(key) if audio.tags else None
    return val[0] if val else ""