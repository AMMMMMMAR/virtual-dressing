from pathlib import Path

from django.conf import settings
from django.core.files.storage import FileSystemStorage


class ProductImageStorage(FileSystemStorage):
    """
    Save new product uploads into static/images/products while keeping legacy
    media/products files readable.
    """

    def __init__(self, *args, **kwargs):
        static_base_url = settings.STATIC_URL if settings.STATIC_URL.endswith("/") else f"{settings.STATIC_URL}/"
        media_base_url = settings.MEDIA_URL if settings.MEDIA_URL.endswith("/") else f"{settings.MEDIA_URL}/"

        super().__init__(
            location=Path(settings.BASE_DIR) / "static",
            base_url=static_base_url,
        )
        self.legacy_storage = FileSystemStorage(
            location=Path(settings.BASE_DIR) / "media",
            base_url=media_base_url,
        )

    def exists(self, name):
        return super().exists(name) or self.legacy_storage.exists(name)

    def open(self, name, mode="rb"):
        if super().exists(name):
            return super().open(name, mode)
        return self.legacy_storage.open(name, mode)

    def url(self, name):
        if super().exists(name):
            return super().url(name)
        if self.legacy_storage.exists(name):
            return self.legacy_storage.url(name)
        return super().url(name)
