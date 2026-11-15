"""Windows profile folders across current and legacy on-disk layouts."""
import re


def user_profiles(target):
    """Yield existing folders once; missing Users on XP is normal, not a read error."""
    mounts = getattr(target.fs, "mounts", {"c:": None})
    drives = sorted({str(name).upper() for name in mounts if re.fullmatch(r"[A-Za-z]:", str(name))})
    seen = set()
    for drive in drives:
        for layout in ("Users", "Documents and Settings"):
            root = target.fs.path(drive + "/" + layout)
            if not root.exists():
                continue
            for path in sorted(root.iterdir(), key=lambda item: item.name.casefold()):
                if path.is_symlink() or not path.is_dir():
                    continue
                key = str(path.resolve()).casefold()
                if key not in seen:
                    seen.add(key)
                    yield path


def ntfs_volume_serial(target, profile):
    path = str(profile).replace("\\", "/").lstrip("/")
    drive = path.split("/", 1)[0].lower()
    mounts = {str(key).lower(): value for key, value in target.fs.mounts.items()}
    return "%08X" % (mounts[drive].ntfs.serial & 0xFFFFFFFF)
