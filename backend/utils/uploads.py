"""Check compressed archive metadata before any decompression."""
import io
import zipfile
from fastapi import HTTPException


def validate_zip(data: bytes, max_expanded: int) -> None:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries = archive.infolist()
            if len(entries) > 2000 or sum(e.file_size for e in entries) > max_expanded:
                raise HTTPException(413, "Archive expands beyond allowed size")
            names = set()
            for entry in entries:
                if entry.is_dir():
                    continue
                name = entry.filename.rsplit("/", 1)[-1].lower()
                if name in names or entry.flag_bits & 1:
                    raise HTTPException(400, "Archive has duplicate filenames or encrypted entries")
                names.add(name)
                if entry.file_size > 0 and entry.file_size / max(entry.compress_size, 1) > 200:
                    raise HTTPException(413, "Archive compression ratio exceeds limit")
    except zipfile.BadZipFile:
        raise HTTPException(400, "Invalid ZIP archive")
