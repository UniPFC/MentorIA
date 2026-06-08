import os
import subprocess
import datetime
import tarfile
import gnupg
import io
from config.settings import settings
from config.logger import logger
import time
import requests
import psycopg2

def get_backup_dir(date_folder: bool = True) -> str:
    """Get or create backup directory with optional date-based folder"""
    if date_folder:
        date_str = datetime.datetime.now().strftime("%d%m%Y")
        backup_dir = os.path.join(settings.BASE_DIR, 'cache', 'backups', date_str)
    else:
        backup_dir = os.path.join(settings.BASE_DIR, 'cache', 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    return backup_dir

def backup_postgres() -> str:
    """Backup PostgreSQL database using pg_dump"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = get_backup_dir()
    dump_file = os.path.join(backup_dir, f"postgres_backup_{timestamp}.sql")

    cmd = [
        "pg_dump",
        "-h", settings.POSTGRES_HOST,
        "-p", str(settings.POSTGRES_PORT),
        "-U", settings.POSTGRES_USER,
        "-d", settings.POSTGRES_DB,
        "-f", dump_file
    ]

    env = os.environ.copy()
    env['PGPASSWORD'] = settings.POSTGRES_PASSWORD

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
    """Backup Qdrant by creating snapshots and tarring storage"""
    from qdrant_client import QdrantClient

    client = QdrantClient(url=settings.QDRANT_URL)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = get_backup_dir()
    tar_file = os.path.join(backup_dir, f"qdrant_backup_{timestamp}.tar.gz")
    storage_path = getattr(settings, 'QDRANT_STORAGE_DIR', os.getenv('QDRANT_STORAGE_DIR', '/qdrant/storage'))

    try:
        collections = client.get_collections().collections
        for collection in collections:
            name = collection.name
            snapshot = client.create_snapshot(collection_name=name)
            logger.info(f"Snapshot created for collection {name}: {snapshot}")

        if not os.path.isdir(storage_path):
            raise FileNotFoundError(f"Qdrant storage directory not found: {storage_path}")

        with tarfile.open(tar_file, "w:gz") as tar:
            tar.add(storage_path, arcname='qdrant_storage')

        logger.info(f"Qdrant backup created: {tar_file}")
        return tar_file
    except Exception as e:
        logger.error(f"Failed to backup Qdrant: {e}")
        raise

def encrypt_file(file_path: str, passphrase: str) -> str:
    """Encrypt file using GPG symmetric encryption"""
    gpg = gnupg.GPG()
    enc_file = file_path + '.gpg'

    try:
        with open(file_path, 'rb') as f:
            encrypted = gpg.encrypt_file(f, recipients=None, symmetric=True, passphrase=passphrase)

        with open(enc_file, 'wb') as f:
            f.write(encrypted.data)

        os.remove(file_path)
        logger.info(f"File encrypted: {enc_file}")
        return enc_file
    except Exception as e:
        logger.error(f"Failed to encrypt {file_path}: {e}")
        raise

def decrypt_file(file_path: str, passphrase: str, output_path: str = None) -> str:
    """Decrypt a GPG-encrypted file and return the decrypted file path"""
    gpg = gnupg.GPG()

    if output_path is None:
        if file_path.endswith('.gpg'):
            output_path = file_path[:-4]
        else:
            output_path = file_path + '.dec'

    try:
        with open(file_path, 'rb') as f:
            decrypted = gpg.decrypt_file(f, passphrase=passphrase)

        if not decrypted.ok:
            raise ValueError(f"Decryption failed: {decrypted.status}")

        with open(output_path, 'wb') as out_f:
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
        with open(encrypted_file_path, 'rb') as f:
            decrypted = gpg.decrypt_file(f, passphrase=passphrase)
            
        if not decrypted.ok:
            raise ValueError(f"Decryption failed: {decrypted.status}")

        cmd = [
            "psql",
            "-h", settings.POSTGRES_HOST,
            "-p", str(settings.POSTGRES_PORT),
            "-U", settings.POSTGRES_USER,
            "-d", settings.POSTGRES_DB
        ]
        
        env = os.environ.copy()
        env['PGPASSWORD'] = settings.POSTGRES_PASSWORD

        process = subprocess.Popen(cmd, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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
        with open(encrypted_file_path, 'rb') as f:
            decrypted = gpg.decrypt_file(f, passphrase=passphrase)
            
        if not decrypted.ok:
            raise ValueError(f"Decryption failed: {decrypted.status}")

        file_like_object = io.BytesIO(decrypted.data)
        
        with tarfile.open(fileobj=file_like_object, mode="r:gz") as tar:
            tar.extractall(path=extract_path, filter='data')
            
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
                database=settings.POSTGRES_DB
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
    date_str: str = None,
    passphrase: str = None,
    second_pass: bool = False
):
    """Restore all backups from a specific date directly into memory/services"""

    wait_for_postgres_ready()
    wait_for_qdrant_ready()

    if date_str is None:
        date_str = datetime.datetime.now().strftime("%d%m%Y")

    if passphrase is None:
        passphrase = os.getenv('BACKUP_PASSPHRASE')
        if not passphrase:
            raise ValueError("BACKUP_PASSPHRASE not set")

    backup_date_dir = os.path.join(
        settings.BASE_DIR,
        'cache',
        'backups',
        date_str
    )

    if not os.path.exists(backup_date_dir):
        logger.error(f"Backup directory not found: {backup_date_dir}")
        raise FileNotFoundError(
            f"No backups found for date {date_str}"
        )

    try:
        for filename in os.listdir(backup_date_dir):
            if not filename.endswith('.gpg'):
                continue

            encrypted_path = os.path.join(
                backup_date_dir,
                filename
            )

            if "postgres_backup" in filename:
                logger.info(
                    f"Restoring PostgreSQL from: {filename}"
                )

                restore_postgres_in_memory(
                    encrypted_path,
                    passphrase
                )

            elif "data_backup" in filename:
                logger.info(f"Restoring Data from: {filename}")

                extract_path = os.path.dirname(
                    settings.DATA_DIR
                )

                restore_tar_in_memory(
                    encrypted_path,
                    passphrase,
                    extract_path
                )

            elif "qdrant_backup" in filename:
                logger.info(f"Restoring Qdrant from: {filename}")

                restore_tar_in_memory(
                    encrypted_path,
                    passphrase,
                    "/qdrant/storage"
                )

        # roda uma segunda vez automaticamente
        if not second_pass:
            logger.info("Running second restore pass...")

            restore_backups(
                date_str=date_str,
                passphrase=passphrase,
                second_pass=True
            )

        logger.info(
            f"All backups restored successfully for date {date_str}"
        )
    except Exception as e:
        logger.error(
            f"Failed to restore backups for date {date_str}: {e}"
        )
        raise


def main():
    """Main backup function"""
    passphrase = os.getenv('BACKUP_PASSPHRASE')
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

def cleanup_old_backups(days: int = 7, base_dir: str = None):
    """Remove backup date folders older than specified days"""
    import time
    
    if base_dir is None:
        base_dir = os.path.join(settings.BASE_DIR, 'cache', 'backups')
    
    cutoff = time.time() - (days * 86400)
    
    try:
        for foldername in os.listdir(base_dir):
            folder_path = os.path.join(base_dir, foldername)
            
            # Skip non-directory entries and special folders
            if not os.path.isdir(folder_path) or foldername == 'DECRYPTED':
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
