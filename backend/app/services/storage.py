"""Original document persistence in local disk or private Supabase Storage."""

from pathlib import Path

from app.core.config import settings


def store_document(local_path: Path, object_key: str) -> str:
    if not settings.supabase_enabled:
        return str(local_path)
    from supabase import create_client

    client = create_client(settings.supabase_url, settings.supabase_secret_key)
    with local_path.open("rb") as source:
        client.storage.from_(settings.supabase_storage_bucket).upload(
            path=object_key,
            file=source,
            file_options={"upsert": "false"},
        )
    local_path.unlink(missing_ok=True)
    return object_key


def delete_document_file(stored_path: str) -> None:
    if settings.supabase_enabled:
        from supabase import create_client

        client = create_client(settings.supabase_url, settings.supabase_secret_key)
        client.storage.from_(settings.supabase_storage_bucket).remove([stored_path])
    else:
        Path(stored_path).unlink(missing_ok=True)
