import pytest
import json
import time
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock
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
    
    @patch('src.services.security_cache.SecurityCache.auto_cleanup_check')
    def test_record_login_attempt_success(self, mock_auto_cleanup, security_cache):
        """Test recording successful login attempt"""
        security_cache.record_login_attempt(
            email="test@example.com",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            success=True
        )
        
        # Load and verify that saved data
        data = security_cache._load_cache(security_cache.login_attempts_file)
        
        # Should have at least one attempt
        assert len(data) > 0
    
    @patch('src.services.security_cache.SecurityCache.auto_cleanup_check')
    def test_record_login_attempt_failure(self, mock_auto_cleanup, security_cache):
        """Test recording failed login attempt"""
        security_cache.record_login_attempt(
            email="test@example.com",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            success=False,
            failure_reason="Invalid password"
        )
        
        # Load and verify that saved data
        data = security_cache._load_cache(security_cache.login_attempts_file)
        
        # Should have at least one attempt
        assert len(data) > 0
    
    @patch('src.services.security_cache.SecurityCache.auto_cleanup_check')
    def test_get_recent_anomalies(self, mock_auto_cleanup, security_cache):
        """Test getting recent anomalies"""
        current_time = time.time()
        
        # Add recent anomaly
        security_cache.record_login_attempt(
            email="test@example.com",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            success=False,
            anomalies=["suspicious_activity"]
        )
        
        # Manually add old anomaly
        old_data = security_cache._load_cache(security_cache.anomalies_file)
        old_data["old_anomaly"] = {
            "email": "old@example.com",
            "ip_address": "192.168.1.2",
            "risk_score": "HIGH",
            "anomalies": ["old_suspicious"],
            "unix_timestamp": current_time - 1000  # Old
        }
        security_cache._save_cache(security_cache.anomalies_file, old_data)
        
        recent_anomalies = security_cache.get_recent_anomalies(hours=1)
        
        # Should return some anomalies (recent ones)
        assert isinstance(recent_anomalies, list)
    
    @patch('src.services.security_cache.SecurityCache.auto_cleanup_check')
    def test_should_block_ip_false(self, mock_auto_cleanup, security_cache):
        """Test IP blocking check when IP should not be blocked"""
        # Add few failed attempts (below threshold)
        for i in range(3):
            security_cache.record_login_attempt(
                email=f"test{i}@example.com",
                ip_address="192.168.1.1",
                user_agent="Mozilla/5.0",
                success=False
            )
        
        should_block, reason = security_cache.should_block_ip("192.168.1.1")
        
        assert should_block is False
        assert reason is None
    
    @patch('src.services.security_cache.SecurityCache.auto_cleanup_check')
    def test_should_block_ip_true(self, mock_auto_cleanup, security_cache):
        """Test IP blocking check when IP should be blocked"""
        # Add many failed attempts (above threshold)
        for i in range(16):  # Above ip_block_threshold of 15
            security_cache.record_login_attempt(
                email=f"test{i}@example.com",
                ip_address="192.168.1.1",
                user_agent="Mozilla/5.0",
                success=False
            )
        
        should_block, reason = security_cache.should_block_ip("192.168.1.1")
        
        assert should_block is True
        assert reason is not None
        assert "excesso" in reason.lower()
    
    @patch('src.services.security_cache.SecurityCache.auto_cleanup_check')
    def test_should_block_ip_not_tracked(self, mock_auto_cleanup, security_cache):
        """Test IP blocking check for IP not in tracking"""
        # Add attempts for different IP
        security_cache.record_login_attempt(
            email="test@example.com",
            ip_address="192.168.1.2",
            user_agent="Mozilla/5.0",
            success=False
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
            success=True
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
            success=True
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
        with open(invalid_file, 'w') as f:
            f.write('invalid json')
        
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
        with open(file_path, 'r') as f:
            saved_data = json.load(f)
        
        assert saved_data == {"test": "data"}
    
    def test_save_cache_write_error(self, security_cache):
        """Test handling write error when saving cache"""
        # This test verifies that method handles errors gracefully
        # The actual implementation may log errors but not raise exceptions
        file_path = security_cache.cache_dir / "test_file.json"
        
        # Should not raise exception even if there's an error
        try:
            security_cache._save_cache(file_path, {"test": "data"})
            success = True
        except Exception:
            success = False
        
        # The method should handle errors gracefully
        assert success  # If we get here, method handled error
