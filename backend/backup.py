"""
Backup and restore functionality for database and Redis.
Implements automatic backups with retention policy.
"""

from __future__ import annotations

import asyncio
import gzip
import json
import logging
import os
import shutil
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Optional

from backend.config import (
    BACKUP_ENABLED,
    BACKUP_INTERVAL_HOURS,
    BACKUP_PATH,
    DATABASE_URL,
    REDIS_URL,
    AWS_S3_BUCKET,
    AWS_REGION,
)

logger = logging.getLogger(__name__)


class BackupManager:
    """Manages database and Redis backups."""
    
    def __init__(self, backup_path: str = BACKUP_PATH):
        self.backup_path = Path(backup_path)
        self.backup_path.mkdir(parents=True, exist_ok=True)
        self.timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        self.backup_dir = self.backup_path / self.timestamp
    
    def backup_database(self) -> tuple[bool, str]:
        """
        Backup PostgreSQL database.
        Returns (success, message)
        """
        if "sqlite" in DATABASE_URL:
            return self._backup_sqlite()
        elif "postgresql" in DATABASE_URL:
            return self._backup_postgresql()
        else:
            return False, f"Unsupported database: {DATABASE_URL}"
    
    def _backup_sqlite(self) -> tuple[bool, str]:
        """Backup SQLite database."""
        try:
            db_path = Path(DATABASE_URL.replace("sqlite:///", ""))
            
            if not db_path.exists():
                return False, f"SQLite database not found: {db_path}"
            
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            backup_file = self.backup_dir / "radar_precios.db"
            
            shutil.copy2(db_path, backup_file)
            
            logger.info(f"SQLite backup created: {backup_file}")
            return True, f"SQLite backup created: {backup_file}"
        
        except Exception as e:
            logger.error(f"SQLite backup failed: {e}")
            return False, f"SQLite backup failed: {e}"
    
    def _backup_postgresql(self) -> tuple[bool, str]:
        """Backup PostgreSQL database using pg_dump."""
        try:
            # Parse DATABASE_URL
            # Format: postgresql://user:password@host:port/dbname
            db_url = DATABASE_URL
            
            # Extract components
            # This is a simplified approach; use psycopg2.extensions.parse_dsn for production
            parts = db_url.replace("postgresql://", "").split("/")
            dbname = parts[-1]
            
            creds = parts[0].split("@")[0]
            user, password = creds.split(":")
            
            host_port = parts[0].split("@")[1]
            host = host_port.split(":")[0]
            port = host_port.split(":")[1] if ":" in host_port else "5432"
            
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            backup_file = self.backup_dir / "radar_precios.sql"
            
            # Create dump
            env = os.environ.copy()
            env["PGPASSWORD"] = password
            
            cmd = [
                "pg_dump",
                "-h", host,
                "-p", port,
                "-U", user,
                "-d", dbname,
                "-f", str(backup_file),
            ]
            
            subprocess.run(cmd, env=env, check=True, capture_output=True)
            
            # Compress
            with open(backup_file, "rb") as f_in:
                with gzip.open(f"{backup_file}.gz", "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            backup_file.unlink()  # Remove uncompressed file
            
            logger.info(f"PostgreSQL backup created: {backup_file}.gz")
            return True, f"PostgreSQL backup created: {backup_file}.gz"
        
        except Exception as e:
            logger.error(f"PostgreSQL backup failed: {e}")
            return False, f"PostgreSQL backup failed: {e}"
    
    def backup_redis(self) -> tuple[bool, str]:
        """Backup Redis database."""
        try:
            import redis
            
            # Parse Redis URL
            # Format: redis://:password@host:port/db
            redis_client = redis.from_url(REDIS_URL, decode_responses=True)
            
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            backup_file = self.backup_dir / "redis_dump.json"
            
            # Get all keys and values
            keys = redis_client.keys("*")
            data = {}
            
            for key in keys:
                key_type = redis_client.type(key)
                
                if key_type == "string":
                    data[key] = redis_client.get(key)
                elif key_type == "list":
                    data[key] = redis_client.lrange(key, 0, -1)
                elif key_type == "set":
                    data[key] = list(redis_client.smembers(key))
                elif key_type == "hash":
                    data[key] = redis_client.hgetall(key)
                elif key_type == "zset":
                    data[key] = redis_client.zrange(key, 0, -1, withscores=True)
            
            # Write to file
            with open(backup_file, "w") as f:
                json.dump(data, f, indent=2, default=str)
            
            logger.info(f"Redis backup created: {backup_file}")
            return True, f"Redis backup created: {backup_file}"
        
        except Exception as e:
            logger.error(f"Redis backup failed: {e}")
            return False, f"Redis backup failed: {e}"
    
    def backup_all(self) -> dict[str, tuple[bool, str]]:
        """Backup both database and Redis."""
        results = {
            "database": self.backup_database(),
            "redis": self.backup_redis(),
        }
        
        # Overall status
        success = all(r[0] for r in results.values())
        logger.info(f"Backup completed: {results}")
        
        return results
    
    def upload_to_s3(self) -> tuple[bool, str]:
        """Upload backups to AWS S3."""
        try:
            import boto3
            
            if not AWS_S3_BUCKET:
                return False, "AWS_S3_BUCKET not configured"
            
            s3_client = boto3.client("s3", region_name=AWS_REGION)
            
            for file_path in self.backup_dir.glob("*"):
                s3_key = f"backups/{self.timestamp}/{file_path.name}"
                
                s3_client.upload_file(
                    str(file_path),
                    AWS_S3_BUCKET,
                    s3_key,
                )
                
                logger.info(f"Uploaded to S3: {s3_key}")
            
            return True, f"Backups uploaded to S3: {AWS_S3_BUCKET}/{self.timestamp}"
        
        except Exception as e:
            logger.error(f"S3 upload failed: {e}")
            return False, f"S3 upload failed: {e}"
    
    def cleanup_old_backups(self, retention_days: int = 30) -> tuple[bool, str]:
        """Remove backups older than retention_days."""
        try:
            cutoff_date = datetime.now(UTC) - timedelta(days=retention_days)
            count = 0
            
            for backup_dir in self.backup_path.iterdir():
                if not backup_dir.is_dir():
                    continue
                
                # Parse timestamp from directory name: YYYYMMDD_HHMMSS
                try:
                    dir_date = datetime.strptime(
                        backup_dir.name, "%Y%m%d_%H%M%S"
                    ).replace(tzinfo=UTC)
                    
                    if dir_date < cutoff_date:
                        shutil.rmtree(backup_dir)
                        logger.info(f"Deleted old backup: {backup_dir}")
                        count += 1
                except ValueError:
                    # Skip directories that don't match the expected format
                    pass
            
            msg = f"Cleaned up {count} old backups (>{retention_days} days)"
            logger.info(msg)
            return True, msg
        
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            return False, f"Cleanup failed: {e}"
    
    def restore_database(self, backup_timestamp: str) -> tuple[bool, str]:
        """Restore database from backup."""
        try:
            backup_dir = self.backup_path / backup_timestamp
            
            if not backup_dir.exists():
                return False, f"Backup not found: {backup_timestamp}"
            
            if "sqlite" in DATABASE_URL:
                backup_file = backup_dir / "radar_precios.db"
                db_path = Path(DATABASE_URL.replace("sqlite:///", ""))
                
                if not backup_file.exists():
                    return False, f"Backup file not found: {backup_file}"
                
                # Create backup of current database before restore
                shutil.copy2(db_path, f"{db_path}.backup")
                
                # Restore
                shutil.copy2(backup_file, db_path)
                
                logger.info(f"Database restored from {backup_file}")
                return True, f"Database restored from {backup_file}"
            
            elif "postgresql" in DATABASE_URL:
                backup_file = backup_dir / "radar_precios.sql.gz"
                
                if not backup_file.exists():
                    return False, f"Backup file not found: {backup_file}"
                
                # Decompress
                sql_file = backup_dir / "radar_precios.sql"
                with gzip.open(backup_file, "rb") as f_in:
                    with open(sql_file, "wb") as f_out:
                        shutil.copyfileobj(f_in, f_out)
                
                # Restore (this is a simplified example)
                logger.info("PostgreSQL restore requires manual intervention")
                return False, "PostgreSQL restore requires manual intervention"
            
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return False, f"Restore failed: {e}"


def create_backup_task():
    """Create Celery task for scheduled backups."""
    # This will be used in backend/tasks.py
    from backend.celery_app import celery_app
    
    @celery_app.task(bind=True, max_retries=3)
    def backup_all(self):
        """Scheduled backup task."""
        try:
            manager = BackupManager()
            results = manager.backup_all()
            
            # Optional: upload to S3
            if AWS_S3_BUCKET:
                manager.upload_to_s3()
            
            # Cleanup old backups
            manager.cleanup_old_backups(retention_days=30)
            
            logger.info(f"Backup task completed: {results}")
            return results
        
        except Exception as exc:
            logger.error(f"Backup task failed: {exc}")
            raise self.retry(exc=exc, countdown=300)  # Retry in 5 minutes
    
    return backup_all
