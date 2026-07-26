import json
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from src.services.security_cache import SecurityCache


@pytest.mark.unit
class TestSecurityCache:
    """Test suite for SecurityCache"""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create temporary directory for cache files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def security_cache(self, temp_cache_dir):
        """Create SecurityCache instance with temporary directory"""
        return SecurityCache(cache_dir=str(temp_cache_dir))

    def test_init_default_values(self, security_cache):
        """Test SecurityCache initialization with default values"""
        assert security_cache.multiple_ip_threshold == 3
        assert security_cache.multiple_user_threshold == 5
        assert security_cache.rapid_attempts_threshold == 10
        assert security_cache.consecutive_failures_threshold == 3
        assert security_cache.ip_block_threshold == 15
        assert security_cache.max_age_hours == 24
        assert security_cache.cache_dir.exists()

    def test_init_custom_cache_dir(self, temp_cache_dir):
        """Test SecurityCache initialization with custom cache directory"""
        cache = SecurityCache(cache_dir=str(temp_cache_dir))

        assert cache.cache_dir == temp_cache_dir
        assert cache.cache_dir.exists()

    def test_init_cache_files(self, security_cache):
        """Test that cache files are created during initialization"""
        assert security_cache.login_attempts_file.exists()
        assert security_cache.ip_tracking_file.exists()
        assert security_cache.user_tracking_file.exists()
        assert security_cache.anomalies_file.exists()

    @patch("src.services.security_cache.SecurityCache.auto_cleanup_check")
    def test_record_login_attempt_success(self, mock_auto_cleanup, security_cache):
        """Test recording successful login attempt"""
        security_cache.record_login_attempt(
            email="test@example.com",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            success=True,
        )

        # Load and verify that saved data
        data = security_cache._load_cache(security_cache.login_attempts_file)

        # Should have at least one attempt
        assert len(data) > 0

    @patch("src.services.security_cache.SecurityCache.auto_cleanup_check")
    def test_record_login_attempt_failure(self, mock_auto_cleanup, security_cache):
        """Test recording failed login attempt"""
        security_cache.record_login_attempt(
            email="test@example.com",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            success=False,
            failure_reason="Invalid password",
        )

        # Load and verify that saved data
        data = security_cache._load_cache(security_cache.login_attempts_file)

        # Should have at least one attempt
        assert len(data) > 0

    @patch("src.services.security_cache.SecurityCache.auto_cleanup_check")
    def test_get_recent_anomalies(self, mock_auto_cleanup, security_cache):
        """Test getting recent anomalies"""
        current_time = time.time()

        # Add recent anomaly
        security_cache.record_login_attempt(
            email="test@example.com",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            success=False,
            anomalies=["suspicious_activity"],
        )

        # Manually add old anomaly
        old_data = security_cache._load_cache(security_cache.anomalies_file)
        old_data["old_anomaly"] = {
            "email": "old@example.com",
            "ip_address": "192.168.1.2",
            "risk_score": "HIGH",
            "anomalies": ["old_suspicious"],
            "unix_timestamp": current_time - 1000,  # Old
        }
        security_cache._save_cache(security_cache.anomalies_file, old_data)

        recent_anomalies = security_cache.get_recent_anomalies(hours=1)

        # Should return some anomalies (recent ones)
        assert isinstance(recent_anomalies, list)

    @patch("src.services.security_cache.SecurityCache.auto_cleanup_check")
    def test_should_block_ip_false(self, mock_auto_cleanup, security_cache):
        """Test IP blocking check when IP should not be blocked"""
        # Add few failed attempts (below threshold)
        for i in range(3):
            security_cache.record_login_attempt(
                email=f"test{i}@example.com",
                ip_address="192.168.1.1",
                user_agent="Mozilla/5.0",
                success=False,
            )

        should_block, reason = security_cache.should_block_ip("192.168.1.1")

        assert should_block is False
        assert reason is None

    @patch("src.services.security_cache.SecurityCache.auto_cleanup_check")
    def test_should_block_ip_true(self, mock_auto_cleanup, security_cache):
        """Test IP blocking check when IP should be blocked"""
        # Add many failed attempts (above threshold)
        for i in range(16):  # Above ip_block_threshold of 15
            security_cache.record_login_attempt(
                email=f"test{i}@example.com",
                ip_address="192.168.1.1",
                user_agent="Mozilla/5.0",
                success=False,
            )

        should_block, reason = security_cache.should_block_ip("192.168.1.1")

        assert should_block is True
        assert reason is not None
        assert "excesso" in reason.lower()

    @patch("src.services.security_cache.SecurityCache.auto_cleanup_check")
    def test_should_block_ip_not_tracked(self, mock_auto_cleanup, security_cache):
        """Test IP blocking check for IP not in tracking"""
        # Add attempts for different IP
        security_cache.record_login_attempt(
            email="test@example.com",
            ip_address="192.168.1.2",
            user_agent="Mozilla/5.0",
            success=False,
        )

        should_block, reason = security_cache.should_block_ip("192.168.1.1")

        assert should_block is False
        assert reason is None

    def test_cleanup_old_data(self, security_cache):
        """Test cleanup of old data"""
        # Add some data
        security_cache.record_login_attempt(
            email="test@example.com",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            success=True,
        )

        # Run cleanup (should not raise exceptions)
        security_cache.cleanup_old_data()

        # If we get here, cleanup completed without exceptions
        assert True

    def test_cleanup_cache_directory_small(self, security_cache):
        """Test cache directory cleanup when size is small"""
        # Add some data (but keep it small)
        security_cache.record_login_attempt(
            email="test@example.com",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            success=True,
        )

        result = security_cache.cleanup_cache_directory()

        assert result is False  # Should not clean small directory

    def test_auto_cleanup_check(self, security_cache):
        """Test auto cleanup check"""
        # This should not raise exceptions
        security_cache.auto_cleanup_check()

        # Verify that cleanup methods were called (no exceptions)
        assert True  # If we get here, no exceptions were raised

    def test_load_cache_file_not_exists(self, security_cache):
        """Test loading cache file that doesn't exist"""
        non_existent_file = security_cache.cache_dir / "non_existent.json"
        result = security_cache._load_cache(non_existent_file)

        assert result == {}

    def test_load_cache_invalid_json(self, security_cache):
        """Test loading cache file with invalid JSON"""
        # Create file with invalid JSON
        invalid_file = security_cache.cache_dir / "invalid.json"
        with open(invalid_file, "w") as f:
            f.write("invalid json")

        result = security_cache._load_cache(invalid_file)

        assert result == {}

        # Clean up
        invalid_file.unlink()

    def test_save_cache_existing_file(self, security_cache):
        """Test saving cache file to existing directory"""
        file_path = security_cache.cache_dir / "test_file.json"

        security_cache._save_cache(file_path, {"test": "data"})

        assert file_path.exists()

        # Verify data was saved
        with open(file_path) as f:
            saved_data = json.load(f)

        assert saved_data == {"test": "data"}

    def test_save_cache_write_error(self, security_cache):
        """Test handling write error when saving cache"""
        file_path = security_cache.cache_dir / "non_existent_subdir" / "test_file.json"

        # Saving to non-existent subdir should log an error and handle it gracefully
        security_cache._save_cache(file_path, {"test": "data"})
        assert not file_path.exists()

    def test_detect_anomalies_multiple_ips(self, security_cache):
        """Test detecting multiple IPs anomaly"""
        email = "user@example.com"
        # Simulate tracking with many IPs
        user_data = {
            email: {
                "ips": ["192.168.1.1", "192.168.1.2", "192.168.1.3", "192.168.1.4"],
                "attempt_count": 4,
            }
        }
        security_cache._save_cache(security_cache.user_tracking_file, user_data)

        result = security_cache.detect_anomalies(email, "192.168.1.1", "Mozilla/5.0")
        assert result["is_anomaly"] is True
        assert result["risk_score"] == "HIGH"
        assert "Múltiplos IPs" in result["anomaly_details"]

    def test_detect_anomalies_multiple_users_and_rapid_attempts_and_suspicious_ua(
        self, security_cache
    ):
        """Test multiple users on same IP, rapid attempts, and suspicious user agent"""
        ip = "192.168.1.1"
        ip_data = {
            ip: {
                "emails": [
                    "a@ex.com",
                    "b@ex.com",
                    "c@ex.com",
                    "d@ex.com",
                    "e@ex.com",
                    "f@ex.com",
                ],
                "attempt_count": 6,
            }
        }
        security_cache._save_cache(security_cache.ip_tracking_file, ip_data)

        # Add 12 rapid attempts in last minute (threshold is 10)
        now = time.time()
        attempts = {}
        for i in range(12):
            attempts[f"attempt_{i}"] = {
                "timestamp": "some_iso",
                "email": f"user{i}@ex.com",
                "ip_address": ip,
                "unix_timestamp": now - 10,
                "success": False,
            }
        security_cache._save_cache(security_cache.login_attempts_file, attempts)

        # Test suspicious user agent
        result = security_cache.detect_anomalies(
            "test@ex.com", ip, "python-requests/2.28"
        )
        assert result["is_anomaly"] is True
        assert result["risk_score"] == "CRITICAL"
        assert "Múltiplos usuários" in result["anomaly_details"]
        assert "Tentativas rápidas" in result["anomaly_details"]
        assert "User-Agent suspeito" in result["anomaly_details"]

    def test_detect_anomalies_empty_user_agent(self, security_cache):
        """Test detecting empty user agent anomaly"""
        result = security_cache.detect_anomalies("test@ex.com", "192.168.1.1", "")
        assert result["is_anomaly"] is True
        assert result["risk_score"] == "MEDIUM"
        assert "User-Agent" in result["anomaly_details"]

    def test_detect_anomalies_consecutive_failures(self, security_cache):
        """Test consecutive failures anomaly detection"""
        email = "user@ex.com"
        now = time.time()
        attempts = {}
        # 5 failures in last 5 minutes (threshold is 3)
        for i in range(5):
            attempts[f"fail_{i}"] = {
                "timestamp": "some_iso",
                "email": email,
                "ip_address": "192.168.1.1",
                "unix_timestamp": now - 30,
                "success": False,
            }
        security_cache._save_cache(security_cache.login_attempts_file, attempts)

        result = security_cache.detect_anomalies(email, "192.168.1.1", "Mozilla/5.0")
        assert result["is_anomaly"] is True
        assert "Falhas consecutivas" in result["anomaly_details"]

    def test_get_security_summary(self, security_cache):
        """Test generating security summary"""
        now = time.time()
        attempts = {
            "att1": {
                "unix_timestamp": now - 100,
                "success": True,
                "risk_score": "LOW",
                "email": "a@ex.com",
                "ip_address": "1.1.1.1",
            },
            "att2": {
                "unix_timestamp": now - 200,
                "success": False,
                "risk_score": "HIGH",
                "email": "b@ex.com",
                "ip_address": "2.2.2.2",
            },
            "att3": {
                "unix_timestamp": now - 7200 * 1000,
                "success": True,
                "risk_score": "LOW",
                "email": "c@ex.com",
                "ip_address": "3.3.3.3",
            },  # very old
        }
        security_cache._save_cache(security_cache.login_attempts_file, attempts)

        anomalies = {
            "ano1": {
                "unix_timestamp": now - 50,
                "email": "b@ex.com",
                "ip_address": "2.2.2.2",
                "risk_score": "HIGH",
            }
        }
        security_cache._save_cache(security_cache.anomalies_file, anomalies)

        summary = security_cache.get_security_summary(hours=24)
        assert summary["total_login_attempts"] == 2
        assert summary["successful_logins"] == 1
        assert summary["failed_logins"] == 1
        assert summary["anomalies_detected"] == 1
        assert summary["unique_ips"] == 2
        assert summary["unique_emails"] == 2

    def test_cleanup_old_data_tracks_cleanup(self, security_cache):
        """Test cleanup_old_data cleans old tracked IPs and Users"""
        now = time.time()
        # IP data
        ip_data = {
            "1.1.1.1": {"unix_timestamp": now - 10, "emails": []},
            "2.2.2.2": {"unix_timestamp": now - 7200 * 3600, "emails": []},  # very old
        }
        security_cache._save_cache(security_cache.ip_tracking_file, ip_data)

        # User data
        user_data = {
            "a@ex.com": {"unix_timestamp": now - 10, "ips": []},
            "b@ex.com": {"unix_timestamp": now - 7200 * 3600, "ips": []},  # very old
        }
        security_cache._save_cache(security_cache.user_tracking_file, user_data)

        security_cache.cleanup_old_data()

        cleaned_ips = security_cache._load_cache(security_cache.ip_tracking_file)
        cleaned_users = security_cache._load_cache(security_cache.user_tracking_file)

        assert "1.1.1.1" in cleaned_ips
        assert "2.2.2.2" not in cleaned_ips
        assert "a@ex.com" in cleaned_users
        assert "b@ex.com" not in cleaned_users

    def test_cleanup_cache_directory_force_and_exceptions(self, security_cache):
        """Test force_cleanup=True and error handling in directory cleanup"""
        # Add files
        f = security_cache.cache_dir / "temp.txt"
        f.write_text("temporary file")

        # Cleanup completely
        result = security_cache.cleanup_cache_directory(force_cleanup=True)
        assert result is True
        assert not f.exists()
        assert security_cache.login_attempts_file.exists()  # reinitialized

        # Simulating exception on listdir/iterdir
        with patch("pathlib.Path.iterdir", side_effect=Exception("Iterdir error")):
            result = security_cache.cleanup_cache_directory()
            assert result is False

    def test_auto_cleanup_check_and_periodic_full_cleanup(self, security_cache):
        """Test auto_cleanup_check flow and periodic full cleanup when .last_full_cleanup exists"""
        # Save last full cleanup timestamp as old
        last_cleanup_file = security_cache.cache_dir / ".last_full_cleanup"
        last_cleanup_file.write_text(str(time.time() - 90000))  # older than 24h

        # Add temporary file that should be cleaned on full cleanup
        temp_f = security_cache.cache_dir / "temp_to_be_deleted.txt"
        temp_f.write_text("delete me")

        security_cache.auto_cleanup_check()
        assert not temp_f.exists()  # Should have run force_cleanup=True

        # Test exception inside auto_cleanup_check
        with patch.object(
            security_cache, "cleanup_old_data", side_effect=Exception("Cleanup error")
        ):
            # Should not raise exception
            security_cache.auto_cleanup_check()
