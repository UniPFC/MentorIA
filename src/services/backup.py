import os
import subprocess
import datetime
import tarfile
import gnupg
from config.settings import settings
from config.logger import logger

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

    try:
        collections = client.get_collections().collections
        for collection in collections:
            name = collection.name
            snapshot = client.create_snapshot(collection_name=name)
            logger.info(f"Snapshot created for collection {name}: {snapshot}")

        # Tar the entire Qdrant storage directory
        with tarfile.open(tar_file, "w:gz") as tar:
            tar.add("/qdrant/storage", arcname="qdrant_storage")

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

def decrypt_file(encrypted_file_path: str, passphrase: str, output_path: str = None) -> str:
    """Decrypt GPG encrypted file"""
    gpg = gnupg.GPG()
    
    if output_path is None:
        output_path = encrypted_file_path.replace('.gpg', '')
    
    try:
        with open(encrypted_file_path, 'rb') as f:
            decrypted = gpg.decrypt_file(f, passphrase=passphrase)
        
        if not decrypted.ok:
            raise ValueError(f"Decryption failed: {decrypted.status}")
        
        with open(output_path, 'wb') as f:
            f.write(decrypted.data)
        
        logger.info(f"File decrypted: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Failed to decrypt {encrypted_file_path}: {e}")
        raise

def decrypt_backups(date_str: str = None, passphrase: str = None, output_dir: str = None) -> list:
    """Decrypt all backups from a specific date
    
    Args:
        date_str: Date in format "15052026" (ddmmyyyy). If None, uses today's date
        passphrase: Decryption passphrase. If None, uses BACKUP_PASSPHRASE env var
        output_dir: Directory to save decrypted files. If None, creates DECRYPTED folder inside backup date folder
    
    Returns:
        List of decrypted file paths
    """
    if date_str is None:
        date_str = datetime.datetime.now().strftime("%d%m%Y")
    
    if passphrase is None:
        passphrase = os.getenv('BACKUP_PASSPHRASE')
        if not passphrase:
            raise ValueError("BACKUP_PASSPHRASE not set")
    
    backup_date_dir = os.path.join(settings.BASE_DIR, 'cache', 'backups', date_str)
    
    if not os.path.exists(backup_date_dir):
        logger.error(f"Backup directory not found: {backup_date_dir}")
        raise FileNotFoundError(f"No backups found for date {date_str}")
    
    if output_dir is None:
        output_dir = os.path.join(backup_date_dir, 'DECRYPTED')
    
    os.makedirs(output_dir, exist_ok=True)
    
    decrypted_files = []
    
    try:
        for filename in os.listdir(backup_date_dir):
            # Skip DECRYPTED folder
            if filename == 'DECRYPTED':
                continue
            
            if filename.endswith('.gpg'):
                encrypted_path = os.path.join(backup_date_dir, filename)
                decrypted_filename = filename.replace('.gpg', '')
                output_path = os.path.join(output_dir, decrypted_filename)
                
                decrypted_path = decrypt_file(encrypted_path, passphrase, output_path)
                decrypted_files.append(decrypted_path)
                logger.info(f"Backup decrypted: {decrypted_filename}")
        
        logger.info(f"Total files decrypted: {len(decrypted_files)}")
        return decrypted_files
    
    except Exception as e:
        logger.error(f"Failed to decrypt backups for date {date_str}: {e}")
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

        # Optional: Clean old backups (keep last 7 days)
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
