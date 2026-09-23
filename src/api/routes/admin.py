import datetime
import os
import re
import shutil

from fastapi import APIRouter, Depends, File, HTTPException, Path, UploadFile
from pydantic import BaseModel

from config.logger import logger
from config.settings import settings
from shared.database.models.user import User
from src.api.dependencies import get_current_active_user
from src.services.backup import (
    backup_data,
    backup_postgres,
    backup_qdrant,
    cleanup_old_backups,
    encrypt_file,
    get_backup_dir,
    restore_backups,
)

router = APIRouter()


class BackupResponse(BaseModel):
    success: bool
    message: str
    files: list[str] = []


class BackupListResponse(BaseModel):
    date_folders: list[str]
    current_backups: dict


class RestoreRequest(BaseModel):
    date_str: str
    passphrase: str | None = None


def verify_admin_slug(
    admin_slug: str = Path(..., description="Admin slug for authentication"),
):
    """Verify admin slug for route access"""
    if admin_slug != settings.ADMIN_SLUG:
        raise HTTPException(
            status_code=403, detail="You're not authorized to access this page"
        )
    return True


def verify_admin_user(current_user: User = Depends(get_current_active_user)):
    """Verify that the current user is the system admin"""
    if current_user.email != settings.SYSTEM_USER_EMAIL:
        raise HTTPException(
            status_code=403, detail="You're not authorized to access this page"
        )
    return current_user


@router.get("/admin/{admin_slug}/verify")
async def verify_slug(admin_slug: str, _: bool = Depends(verify_admin_slug)):
    """Verify admin slug without requiring authentication"""
    return {"success": True, "message": "Slug verified"}


@router.post("/admin/{admin_slug}/backup", response_model=BackupResponse)
async def trigger_backup(
    admin_slug: str,
    _: bool = Depends(verify_admin_slug),
    current_user: User = Depends(verify_admin_user),
):
    """Trigger a manual backup of PostgreSQL, data, and Qdrant"""
    try:
        passphrase = os.getenv("BACKUP_PASSPHRASE")
        if not passphrase:
            raise HTTPException(status_code=500, detail="BACKUP_PASSPHRASE not set")

        backups = []

        # Backup PostgreSQL
        postgres_dump = backup_postgres()
        enc_postgres = encrypt_file(postgres_dump, passphrase)
        backups.append(enc_postgres)

        # Backup data
        data_tar = backup_data()
        enc_data = encrypt_file(data_tar, passphrase)
        backups.append(enc_data)

        # Backup Qdrant
        try:
            qdrant_backup = backup_qdrant()
            if qdrant_backup:
                enc_qdrant = encrypt_file(qdrant_backup, passphrase)
                backups.append(enc_qdrant)
        except Exception as e:
            logger.warning(f"Qdrant backup failed: {e}")

        # Cleanup old backups
        cleanup_old_backups(days=7)

        return BackupResponse(
            success=True, message="Backup completed successfully", files=backups
        )
    except Exception as e:
        logger.error(f"Backup failed: {e}")
        raise HTTPException(status_code=500, detail=f"Backup failed: {str(e)}")


@router.get("/admin/{admin_slug}/backups", response_model=BackupListResponse)
async def list_backups(
    admin_slug: str,
    _: bool = Depends(verify_admin_slug),
    current_user: User = Depends(verify_admin_user),
):
    """List all available backup date folders and their contents"""
    try:
        backup_base_dir = get_backup_dir(date_folder=False)

        if not os.path.exists(backup_base_dir):
            return BackupListResponse(date_folders=[], current_backups={})

        date_folders = []
        backups_info = {}

        for foldername in sorted(os.listdir(backup_base_dir), reverse=True):
            folder_path = os.path.join(backup_base_dir, foldername)

            if not os.path.isdir(folder_path):
                continue

            # Check if folder name is in format DDMMYYYY (8 digits)
            if len(foldername) == 8 and foldername.isdigit():
                date_folders.append(foldername)

                # List files in this date folder
                files = []
                for filename in os.listdir(folder_path):
                    file_path = os.path.join(folder_path, filename)
                    if os.path.isfile(file_path):
                        stat = os.stat(file_path)
                        files.append(
                            {
                                "name": filename,
                                "size": stat.st_size,
                                "created": datetime.datetime.fromtimestamp(
                                    stat.st_ctime
                                ).isoformat(),
                            }
                        )

                backups_info[foldername] = files

        return BackupListResponse(
            date_folders=date_folders, current_backups=backups_info
        )
    except Exception as e:
        logger.error(f"Failed to list backups: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list backups: {str(e)}")


@router.post("/admin/{admin_slug}/restore")
async def restore_backup(
    admin_slug: str,
    request: RestoreRequest,
    _: bool = Depends(verify_admin_slug),
    current_user: User = Depends(verify_admin_user),
):
    """Restore backups from a specific date"""
    if not re.match(r"^\d{8}$", request.date_str):
        raise HTTPException(status_code=400, detail="Invalid date format")

    try:
        passphrase = request.passphrase or os.getenv("BACKUP_PASSPHRASE")
        if not passphrase:
            raise HTTPException(status_code=500, detail="BACKUP_PASSPHRASE not set")

        # Dispose connection pool before restore to avoid stale connections after pg_terminate_backend
        from shared.database.session import engine

        engine.dispose()

        restore_backups(date_str=request.date_str, passphrase=passphrase)

        # Format date_str from DDMMYYYY to DD/MM/YYYY
        formatted_date = (
            f"{request.date_str[:2]}/{request.date_str[2:4]}/{request.date_str[4:8]}"
        )

        return BackupResponse(
            success=True,
            message=f"Backup restored successfully for date {formatted_date}",
        )
    except FileNotFoundError as e:
        logger.error(f"Backup not found: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Restore failed: {e}")
        raise HTTPException(status_code=500, detail=f"Restore failed: {str(e)}")


@router.delete("/admin/{admin_slug}/backups/{date_str}")
async def delete_backup(
    admin_slug: str,
    date_str: str,
    _: bool = Depends(verify_admin_slug),
    current_user: User = Depends(verify_admin_user),
):
    """Delete a specific backup date folder"""
    if not re.match(r"^\d{8}$", date_str):
        raise HTTPException(status_code=400, detail="Invalid date format")

    try:
        backup_base_dir = get_backup_dir(date_folder=False)
        backup_date_dir = os.path.join(backup_base_dir, date_str)

        if not os.path.exists(backup_date_dir):
            raise HTTPException(
                status_code=404, detail=f"Backup folder not found: {date_str}"
            )

        import shutil

        shutil.rmtree(backup_date_dir)

        logger.info(f"Deleted backup folder: {date_str}")

        return BackupResponse(
            success=True, message=f"Backup folder {date_str} deleted successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete backup: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to delete backup: {str(e)}"
        )


@router.post("/admin/{admin_slug}/backup/upload", response_model=BackupResponse)
async def upload_backup(
    admin_slug: str,
    file: UploadFile = File(...),
    _: bool = Depends(verify_admin_slug),
    current_user: User = Depends(verify_admin_user),
):
    """Upload a ZIP containing a backup"""
    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only ZIP files are allowed")

    # 1. Limit file size (OOM DoS Prevention)
    if isinstance(file.size, int) and file.size > 100 * 1024 * 1024:
        raise HTTPException(
            status_code=413, detail="Backup file too large (max 100MB)."
        )

    try:
        backup_base_dir = get_backup_dir(date_folder=False)
        tmp_zip_path = None

        try:
            import tempfile
            import zipfile

            with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp_zip:
                tmp_zip_path = tmp_zip.name
                content = await file.read()
                if len(content) > 100 * 1024 * 1024:
                    raise HTTPException(
                        status_code=413, detail="Backup file too large (max 100MB)."
                    )
                tmp_zip.write(content)
                tmp_zip.flush()

            with tempfile.TemporaryDirectory() as extract_dir:
                with zipfile.ZipFile(tmp_zip_path, "r") as zip_ref:
                    # Basic zip slip protection
                    import os

                    for member in zip_ref.namelist():
                        if (
                            ".." in member
                            or member.startswith("/")
                            or member.startswith("\\")
                            or os.path.isabs(member)
                        ):
                            raise HTTPException(
                                status_code=400, detail="Invalid zip file structure."
                            )
                    zip_ref.extractall(extract_dir)

                date_folders_found = []
                files_found = []

                for root, dirs, files in os.walk(extract_dir):
                    for d in dirs:
                        if len(d) == 8 and d.isdigit():
                            date_folders_found.append(os.path.join(root, d))
                    for f in files:
                        if f.endswith(".gpg"):
                            files_found.append(os.path.join(root, f))

                if not files_found:
                    raise HTTPException(
                        status_code=400, detail="No backup files (.gpg) found in ZIP"
                    )

                if date_folders_found:
                    src_folder = date_folders_found[0]
                    folder_name = os.path.basename(src_folder)
                    target_folder = os.path.join(backup_base_dir, folder_name)

                    if os.path.exists(target_folder):
                        shutil.rmtree(target_folder)
                    shutil.copytree(src_folder, target_folder)
                    message = f"Backup uploaded and extracted to {folder_name}"
                else:
                    date_str = datetime.datetime.now().strftime("%d%m%Y")
                    target_folder = os.path.join(backup_base_dir, date_str)
                    if not os.path.exists(target_folder):
                        os.makedirs(target_folder)

                    for gpg_file in files_found:
                        shutil.copy2(
                            gpg_file,
                            os.path.join(target_folder, os.path.basename(gpg_file)),
                        )

                    message = f"Backup uploaded and extracted to {date_str}"

                return BackupResponse(
                    success=True,
                    message=message,
                )
        finally:
            if tmp_zip_path and os.path.exists(tmp_zip_path):
                os.remove(tmp_zip_path)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload backup: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to upload backup: {str(e)}"
        )
