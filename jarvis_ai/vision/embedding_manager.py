"""Embedding Manager — Identity merge and maintenance utilities.

Provides reusable operations for managing the face embeddings database:
merge identities, list identities, prune orphans, etc.

This is a service-level utility, not a one-off script.
"""

from __future__ import annotations

import pickle
import shutil
from pathlib import Path

from jarvis_ai.config import FACE_EMBEDDINGS_DB, FACE_DATASET_DIR
from jarvis_ai.utils.logger import LOGGER


class EmbeddingManager:
    """Manages the face embeddings database for identity maintenance."""

    def __init__(self) -> None:
        self._db: dict[str, list[list[float]]] = {}
        self._load()

    # ── Persistence ──────────────────────────────────────────────────

    def _load(self) -> None:
        if FACE_EMBEDDINGS_DB.exists():
            with FACE_EMBEDDINGS_DB.open("rb") as f:
                self._db = pickle.load(f)
            LOGGER.info("EmbeddingManager: Loaded %d identities.", len(self._db))
        else:
            self._db = {}

    def _save(self) -> None:
        """Save database with automatic backup of the previous version."""
        if FACE_EMBEDDINGS_DB.exists():
            backup = Path(str(FACE_EMBEDDINGS_DB) + ".bak")
            shutil.copy2(FACE_EMBEDDINGS_DB, backup)
            LOGGER.info("EmbeddingManager: Backup saved to %s", backup)

        FACE_EMBEDDINGS_DB.parent.mkdir(parents=True, exist_ok=True)
        with FACE_EMBEDDINGS_DB.open("wb") as f:
            pickle.dump(self._db, f)
        LOGGER.info("EmbeddingManager: Database saved.")

    # ── Queries ──────────────────────────────────────────────────────

    def list_identities(self) -> dict[str, int]:
        """Return a mapping of identity name → embedding count."""
        return {name: len(vecs) for name, vecs in self._db.items()}

    # ── Merge ────────────────────────────────────────────────────────

    def merge(self, source_name: str, target_name: str) -> int:
        """Merge embeddings from source_name INTO target_name.

        After merge:
        - target_name contains the union of both embedding sets.
        - source_name is removed from the database.
        - Face dataset images are moved into the target folder.

        Returns:
            The total number of embeddings in the merged target identity.

        Raises:
            KeyError: If source_name or target_name is not in the database.
        """
        if source_name not in self._db:
            raise KeyError(f"Source identity '{source_name}' not found in database.")
        if target_name not in self._db:
            raise KeyError(f"Target identity '{target_name}' not found in database.")
        if source_name == target_name:
            raise ValueError("Source and target must be different identities.")

        source_vecs = self._db.pop(source_name)
        self._db[target_name].extend(source_vecs)

        merged_count = len(self._db[target_name])
        LOGGER.info(
            "EmbeddingManager: Merged '%s' (%d embeddings) into '%s'. "
            "Total embeddings for '%s': %d",
            source_name, len(source_vecs),
            target_name, target_name, merged_count,
        )

        # Move face dataset images
        source_dir = FACE_DATASET_DIR / source_name
        target_dir = FACE_DATASET_DIR / target_name
        if source_dir.exists():
            target_dir.mkdir(parents=True, exist_ok=True)
            existing_count = len(list(target_dir.glob("img*.jpg")))
            for img in sorted(source_dir.glob("*")):
                existing_count += 1
                dest = target_dir / f"img{existing_count:03d}{img.suffix}"
                shutil.move(str(img), str(dest))
                LOGGER.debug("Moved %s -> %s", img.name, dest.name)
            # Remove the now-empty source directory
            try:
                source_dir.rmdir()
                LOGGER.info("Removed empty directory: %s", source_dir)
            except OSError:
                LOGGER.warning("Could not remove directory: %s", source_dir)

        self._save()
        return merged_count

    def remove_identity(self, name: str) -> None:
        """Completely remove an identity from the database."""
        if name not in self._db:
            raise KeyError(f"Identity '{name}' not found.")
        del self._db[name]
        self._save()
        LOGGER.info("EmbeddingManager: Removed identity '%s'.", name)
