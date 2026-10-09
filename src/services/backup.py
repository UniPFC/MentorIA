import datetime
import io
import os
import subprocess
import tarfile
import time

import gnupg
import psycopg2
import requests

from config.logger import logger
from config.settings import settings


def get_backup_dir(date_folder: bool = True) -> str:
    """Get or create backup directory with optional date-based folder"""
    if date_folder:
        date_str = datetime.datetime.now().strftime("%d%m%Y")
        backup_dir = os.path.join(settings.BASE_DIR, "cache", "backups", date_str)
    else:
        backup_dir = os.path.join(settings.BASE_DIR, "cache", "backups")
    os.makedirs(backup_dir, exist_ok=True)
    return backup_dir


def backup_postgres() -> str:
    """Backup PostgreSQL database using pg_dump"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = get_backup_dir()
    dump_file = os.path.join(backup_dir, f"postgres_backup_{timestamp}.sql")

    cmd = [
        "pg_dump",
        "-h",
        settings.POSTGRES_HOST,
        "-p",
        str(settings.POSTGRES_PORT),
        "-U",
        settings.POSTGRES_USER,
        "-d",
        settings.POSTGRES_DB,
        "-f",
        dump_file,
    ]

    env = os.environ.copy()
    env["PGPASSWORD"] = settings.POSTGRES_PASSWORD

    try:
        subprocess.run(cmd, env=env, check=True, capture_output=True)
        logger.info(f"PostgreSQL backup created: {dump_file}")
        return dump_file
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to backup PostgreSQL: {e}")
        raise


def backup_data() -> str:
    """Backup data directory"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = get_backup_dir()
    tar_file = os.path.join(backup_dir, f"data_backup_{timestamp}.tar.gz")

    try:
        with tarfile.open(tar_file, "w:gz") as tar:
            tar.add(settings.DATA_DIR, arcname="data")
        logger.info(f"Data backup created: {tar_file}")
        return tar_file
    except Exception as e:
        logger.error(f"Failed to backup data: {e}")
        raise


def backup_qdrant() -> str:
    """Backup Qdrant by creating and downloading true collection snapshots"""
    import shutil
    import tempfile

    import requests
    from qdrant_client import QdrantClient

    client = QdrantClient(url=settings.QDRANT_URL)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = get_backup_dir()
    tar_file = os.path.join(backup_dir, f"qdrant_backup_{timestamp}.tar.gz")

    # Create a temporary staging directory to assemble the snapshot tarball
    staging_dir = tempfile.mkdtemp(prefix="qdrant_backup_")

    try:
        collections = client.get_collections().collections
        collections_staging_dir = os.path.join(staging_dir, "collections")
        os.makedirs(collections_staging_dir, exist_ok=True)

        for collection in collections:
            name = collection.name
            logger.info(f"Creating snapshot for collection {name}...")
            snapshot_desc = client.create_snapshot(collection_name=name)
            snapshot_name = snapshot_desc.name
            logger.info(f"Snapshot created on Qdrant server: {snapshot_name}")

            # Download the snapshot file via REST API
            snap_url = (
                f"{settings.QDRANT_URL}/collections/{name}/snapshots/{snapshot_name}"
            )

            # Setup local directory structure mimicking the expected restore layout
            coll_snaps_dir = os.path.join(collections_staging_dir, name, "snapshots")
            os.makedirs(coll_snaps_dir, exist_ok=True)
            local_snap_path = os.path.join(coll_snaps_dir, snapshot_name)

            logger.info(f"Downloading snapshot {snapshot_name} to backup archive...")
            with requests.get(snap_url, stream=True, timeout=60) as r:
                r.raise_for_status()
                with open(local_snap_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)

        # Create the tarball from the downloaded snapshots
        with tarfile.open(tar_file, "w:gz") as tar:
            for item in os.listdir(staging_dir):
                item_path = os.path.join(staging_dir, item)
                tar.add(item_path, arcname=item)

        logger.info(f"Qdrant snapshot backup created successfully: {tar_file}")
        return tar_file
    except Exception as e:
        logger.error(f"Failed to backup Qdrant: {e}")
        raise
    finally:
        try:
            shutil.rmtree(staging_dir)
        except Exception as e:
            logger.warning(f"Could not remove temporary staging dir {staging_dir}: {e}")


def encrypt_file(file_path: str, passphrase: str) -> str:
    """Encrypt file using GPG symmetric encryption"""
    gpg = gnupg.GPG()
    enc_file = file_path + ".gpg"

    try:
        with open(file_path, "rb") as f:
            encrypted = gpg.encrypt_file(
                f, recipients=None, symmetric=True, passphrase=passphrase
            )

        with open(enc_file, "wb") as f:
            f.write(encrypted.data)

        os.remove(file_path)
        logger.info(f"File encrypted: {enc_file}")
        return enc_file
    except Exception as e:
        logger.error(f"Failed to encrypt {file_path}: {e}")
        raise


def decrypt_file(
    file_path: str, passphrase: str, output_path: str | None = None
) -> str:
    """Decrypt a GPG-encrypted file and return the decrypted file path"""
    gpg = gnupg.GPG()

    if output_path is None:
        if file_path.endswith(".gpg"):
            output_path = file_path[:-4]
        else:
            output_path = file_path + ".dec"

    try:
        with open(file_path, "rb") as f:
            decrypted = gpg.decrypt_file(f, passphrase=passphrase)

        if not decrypted.ok:
            raise ValueError(f"Decryption failed: {decrypted.status}")

        with open(output_path, "wb") as out_f:
            out_f.write(decrypted.data)

        os.remove(file_path)
        logger.info(f"File decrypted: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Failed to decrypt {file_path}: {e}")
        raise


def restore_postgres_in_memory(encrypted_file_path: str, passphrase: str):
    """Decrypts PostgreSQL backup and restores directly to the database via memory"""
    gpg = gnupg.GPG()

    try:
        with open(encrypted_file_path, "rb") as f:
            decrypted = gpg.decrypt_file(f, passphrase=passphrase)

        if not decrypted.ok:
            raise ValueError(f"Decryption failed: {decrypted.status}")

        # Drop and recreate database
        logger.info("Dropping and recreating database...")
        drop_recreate_cmd = [
            "psql",
            "-h",
            settings.POSTGRES_HOST,
            "-p",
            str(settings.POSTGRES_PORT),
            "-U",
            settings.POSTGRES_USER,
            "-d",
            "postgres",
        ]

        env = os.environ.copy()
        env["PGPASSWORD"] = settings.POSTGRES_PASSWORD

        drop_recreate_sql = f"""
        SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '{settings.POSTGRES_DB}' AND pid <> pg_backend_pid();
        DROP DATABASE IF EXISTS {settings.POSTGRES_DB};
        CREATE DATABASE {settings.POSTGRES_DB};
        """

        process = subprocess.Popen(
            drop_recreate_cmd,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = process.communicate(input=drop_recreate_sql.encode("utf-8"))

        if process.returncode != 0:
            raise Exception(
                f"Failed to drop/recreate database: {stderr.decode('utf-8')}"
            )

        logger.info("Database dropped and recreated successfully")

        # Restore the backup
        cmd = [
            "psql",
            "-h",
            settings.POSTGRES_HOST,
            "-p",
            str(settings.POSTGRES_PORT),
            "-U",
            settings.POSTGRES_USER,
            "-d",
            settings.POSTGRES_DB,
        ]

        process = subprocess.Popen(
            cmd,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = process.communicate(input=decrypted.data)

        if process.returncode != 0:
            raise Exception(f"psql error: {stderr.decode('utf-8')}")

        logger.info(f"PostgreSQL restored successfully from {encrypted_file_path}")
    except Exception as e:
        logger.error(f"Failed to restore PostgreSQL from memory: {e}")
        raise


def restore_tar_in_memory(encrypted_file_path: str, passphrase: str, extract_path: str):
    """Decrypts tar.gz backup and extracts directly to the target path via memory"""
    gpg = gnupg.GPG()

    try:
        with open(encrypted_file_path, "rb") as f:
            decrypted = gpg.decrypt_file(f, passphrase=passphrase)

        if not decrypted.ok:
            raise ValueError(f"Decryption failed: {decrypted.status}")

        # Clear the extract path before restoring (only if it's a subdirectory, not root)
        if os.path.exists(extract_path) and extract_path != "/app":
            logger.info(f"Clearing directory contents: {extract_path}")
            import shutil

            for item in os.listdir(extract_path):
                item_path = os.path.join(extract_path, item)
                try:
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    else:
                        os.remove(item_path)
                except Exception as e:
                    logger.warning(f"Could not remove {item_path}: {e}")
        elif extract_path == "/app":
            # For /app, only clear data subdirectory contents
            data_path = os.path.join(extract_path, "data")
            if os.path.exists(data_path):
                logger.info(f"Clearing data directory contents: {data_path}")
                import shutil

                for item in os.listdir(data_path):
                    item_path = os.path.join(data_path, item)
                    try:
                        if os.path.isdir(item_path):
                            shutil.rmtree(item_path)
                        else:
                            os.remove(item_path)
                    except Exception as e:
                        logger.warning(f"Could not remove {item_path}: {e}")

        file_like_object = io.BytesIO(decrypted.data)

        with tarfile.open(fileobj=file_like_object, mode="r:gz") as tar:
            tar.extractall(path=extract_path, filter="data")

        logger.info(f"Files extracted successfully to {extract_path}")
    except Exception as e:
        logger.error(f"Failed to extract tar from memory: {e}")
        raise


def wait_for_postgres_ready():
    for _ in range(30):
        try:
            psycopg2.connect(
                host=settings.POSTGRES_HOST,
                port=settings.POSTGRES_PORT,
                user=settings.POSTGRES_USER,
                password=settings.POSTGRES_PASSWORD,
                database=settings.POSTGRES_DB,
            ).close()
            logger.info("PostgreSQL is ready")
            return

        except Exception as e:
            logger.warning(f"PostgreSQL not ready: {e}")
            time.sleep(1)
    else:
        raise Exception("PostgreSQL not ready after 30 attempts")


def wait_for_qdrant_ready():
    for _ in range(30):
        try:
            response = requests.get(f"{settings.QDRANT_URL}/collections")
            if response.status_code == 200:
                logger.info("Qdrant is ready")
                return
            else:
                logger.warning(f"Qdrant not ready, status code: {response.status_code}")
        except Exception as e:
            logger.warning(f"Qdrant not ready: {e}")
        time.sleep(1)
    else:
        raise Exception("Qdrant not ready after 30 attempts")


def restore_backups(
    date_str: str | None = None,
    passphrase: str | None = None,
    second_pass: bool = False,
):
    """Restore all backups from a specific date directly into memory/services"""

    wait_for_postgres_ready()
    wait_for_qdrant_ready()

    if date_str is None:
        date_str = datetime.datetime.now().strftime("%d%m%Y")

    if passphrase is None:
        passphrase = os.getenv("BACKUP_PASSPHRASE")
        if not passphrase:
            raise ValueError("BACKUP_PASSPHRASE not set")

    backup_date_dir = os.path.join(settings.BASE_DIR, "cache", "backups", date_str)

    if not os.path.exists(backup_date_dir):
        logger.error(f"Backup directory not found: {backup_date_dir}")
        raise FileNotFoundError(f"No backups found for date {date_str}")

    try:
        postgres_files = []
        data_files = []
        qdrant_files = []

        for filename in os.listdir(backup_date_dir):
            if not filename.endswith(".gpg"):
                continue

            if "postgres_backup" in filename:
                postgres_files.append(filename)
            elif "data_backup" in filename:
                data_files.append(filename)
            elif "qdrant_backup" in filename:
                qdrant_files.append(filename)

        # Sort to find the latest (works perfectly because of YYYYMMDD_HHMMSS format)
        postgres_files.sort()
        data_files.sort()
        qdrant_files.sort()

        if postgres_files:
            latest_postgres = postgres_files[-1]
            logger.info(f"Restoring PostgreSQL from latest backup: {latest_postgres}")
            restore_postgres_in_memory(
                os.path.join(backup_date_dir, latest_postgres), passphrase
            )

        if data_files:
            latest_data = data_files[-1]
            logger.info(f"Restoring Data from latest backup: {latest_data}")
            extract_path = os.path.dirname(settings.DATA_DIR)
            restore_tar_in_memory(
                os.path.join(backup_date_dir, latest_data), passphrase, extract_path
            )

        if qdrant_files:
            latest_qdrant = qdrant_files[-1]
            logger.info(f"Restoring Qdrant from latest backup: {latest_qdrant}")

            qdrant_storage_path = getattr(
                settings,
                "QDRANT_STORAGE_DIR",
                os.getenv("QDRANT_STORAGE_DIR", "/qdrant/storage"),
            )
            temp_restore_path = os.path.join(qdrant_storage_path, "tmp_restore")

            # Extract to a temporary folder in the shared volume
            restore_tar_in_memory(
                os.path.join(backup_date_dir, latest_qdrant),
                passphrase,
                temp_restore_path,
            )

            # Determine if this is a legacy raw backup or a proper snapshot backup
            import shutil

            is_legacy_backup = True
            collections_dir = os.path.join(temp_restore_path, "collections")

            if os.path.exists(collections_dir):
                for coll_name in os.listdir(collections_dir):
                    snaps_dir = os.path.join(collections_dir, coll_name, "snapshots")
                    if os.path.exists(snaps_dir) and any(
                        f.endswith(".snapshot") for f in os.listdir(snaps_dir)
                    ):
                        is_legacy_backup = False
                        break

            if is_legacy_backup:
                logger.warning(
                    "Legacy raw backup detected (no .snapshot files). Extracting directly to storage. Qdrant MUST be restarted to apply changes."
                )
                # We need to extract directly to the storage path
                try:
                    shutil.rmtree(temp_restore_path)
                except Exception:
                    pass
                restore_tar_in_memory(
                    os.path.join(backup_date_dir, latest_qdrant),
                    passphrase,
                    qdrant_storage_path,
                )
            else:
                # Proper snapshot backup, use the Qdrant REST API
                from qdrant_client import QdrantClient

                client = QdrantClient(url=settings.QDRANT_URL)

                for coll_name in os.listdir(collections_dir):
                    snaps_dir = os.path.join(collections_dir, coll_name, "snapshots")
                    if os.path.exists(snaps_dir):
                        snaps = [
                            f for f in os.listdir(snaps_dir) if f.endswith(".snapshot")
                        ]
                        if snaps:
                            snaps.sort()
                            latest_snap = snaps[-1]

                            snap_path = os.path.join(
                                temp_restore_path,
                                "collections",
                                coll_name,
                                "snapshots",
                                latest_snap,
                            )

                            logger.info(
                                f"Uploading Qdrant snapshot '{coll_name}' via API..."
                            )
                            try:
                                upload_url = f"{settings.QDRANT_URL}/collections/{coll_name}/snapshots/upload?wait=true"
                                with open(snap_path, "rb") as snap_file:
                                    res = requests.post(
                                        upload_url,
                                        files={"snapshot": snap_file},
                                        timeout=300,
                                    )

                                if res.ok:
                                    logger.info(
                                        f"Successfully recovered collection '{coll_name}' via snapshot upload"
                                    )
                                else:
                                    logger.error(
                                        f"Failed to recover '{coll_name}': {res.text}"
                                    )
                            except Exception as e:
                                logger.error(
                                    f"Error calling Qdrant recover API for '{coll_name}': {e}"
                                )

                try:
                    shutil.rmtree(temp_restore_path)
                except Exception as e:
                    logger.warning(
                        f"Could not remove temporary Qdrant restore path: {e}"
                    )

        logger.info(f"All backups restored successfully for date {date_str}")
    except Exception as e:
        logger.error(f"Failed to restore backups for date {date_str}: {e}")
        raise


def main():
    """Main backup function"""
    passphrase = os.getenv("BACKUP_PASSPHRASE")
    if not passphrase:
        logger.error("BACKUP_PASSPHRASE environment variable not set")
        raise ValueError("BACKUP_PASSPHRASE not set")

    backups = []

    try:
        # Backup PostgreSQL
        postgres_dump = backup_postgres()
        enc_postgres = encrypt_file(postgres_dump, passphrase)
        backups.append(enc_postgres)

        # Backup data
        data_tar = backup_data()
        enc_data = encrypt_file(data_tar, passphrase)
        backups.append(enc_data)

        # Backup Qdrant
        qdrant_backup = backup_qdrant()
        if qdrant_backup:
            enc_qdrant = encrypt_file(qdrant_backup, passphrase)
            backups.append(enc_qdrant)

        logger.info(f"Encrypted backups created: {backups}")

        cleanup_old_backups(days=7)

    except Exception as e:
        logger.error(f"Backup failed: {e}")
        raise


def cleanup_old_backups(days: int = 7, base_dir: str | None = None):
    """Remove backup date folders older than specified days"""
    import time

    if base_dir is None:
        base_dir = os.path.join(settings.BASE_DIR, "cache", "backups")

    cutoff = time.time() - (days * 86400)

    try:
        for foldername in os.listdir(base_dir):
            folder_path = os.path.join(base_dir, foldername)

            # Skip non-directory entries and special folders
            if not os.path.isdir(folder_path) or foldername == "DECRYPTED":
                continue

            # Check if folder name is in format DDMMYYYY (8 digits)
            if len(foldername) == 8 and foldername.isdigit():
                if os.path.getmtime(folder_path) < cutoff:
                    import shutil

                    shutil.rmtree(folder_path)
                    logger.info(f"Removed old backup folder: {foldername}")
    except Exception as e:
        logger.error(f"Failed to cleanup old backups: {e}")
        raise


if __name__ == "__main__":
    main()
