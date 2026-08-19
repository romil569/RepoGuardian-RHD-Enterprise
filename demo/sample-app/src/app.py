def normalize_username(value: str) -> str:
    return value.strip().lower()


def can_upload_image(size_mb: int) -> bool:
    return size_mb <= 10
