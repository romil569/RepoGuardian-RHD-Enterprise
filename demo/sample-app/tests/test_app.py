from src.app import can_upload_image, normalize_username


def test_normalize_username() -> None:
    assert normalize_username("  Ada ") == "ada"


def test_can_upload_image() -> None:
    assert can_upload_image(3)
    assert not can_upload_image(12)
