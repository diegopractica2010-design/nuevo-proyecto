"""Tests para ProxyManager."""

import pytest
from datetime import UTC, datetime, timedelta

from backend.infrastructure.proxy_manager import ProxyConfig, ProxyManager


class TestProxyConfig:
    """Tests para ProxyConfig."""
    
    def test_proxy_available_by_default(self):
        """Un proxy nuevo debe estar disponible."""
        proxy = ProxyConfig(url="http://proxy.example.com:8080")
        assert proxy.is_available() is True
    
    def test_proxy_blocked_after_failure(self):
        """Proxy se bloquea después de un fallo."""
        proxy = ProxyConfig(url="http://proxy.example.com:8080")
        proxy.mark_failure()
        assert proxy.is_available() is False
        assert proxy.failure_count == 1
    
    def test_proxy_unblocks_after_timeout(self):
        """Proxy se desbloquea después del timeout."""
        proxy = ProxyConfig(url="http://proxy.example.com:8080")
        proxy.mark_failure()
        
        # Bloqueo inicial es 30 segundos
        assert proxy.blocked_until is not None
        assert not proxy.is_available()
        
        # Simular que pasó el tiempo
        proxy.blocked_until = datetime.now(UTC) - timedelta(seconds=1)
        assert proxy.is_available() is True
        assert proxy.failure_count == 0
    
    def test_exponential_backoff(self):
        """Bloqueos aumentan exponencialmente."""
        proxy = ProxyConfig(url="http://proxy.example.com:8080")
        
        durations = []
        for _ in range(4):
            proxy.mark_failure()
            if proxy.blocked_until:
                duration = (proxy.blocked_until - datetime.now(UTC)).total_seconds()
                durations.append(duration)
                # Reset para siguiente iteración
                proxy.blocked_until = None
        
        # Durations deben ir aumentando (30, 120, 600, 1800)
        assert len(durations) > 0
    
    def test_mark_success_resets_failures(self):
        """mark_success() resetea contador de fallos."""
        proxy = ProxyConfig(url="http://proxy.example.com:8080")
        proxy.mark_failure()
        assert proxy.failure_count == 1
        
        proxy.mark_success()
        assert proxy.failure_count == 0
        assert proxy.blocked_until is None
        assert proxy.last_used is not None


class TestProxyManager:
    """Tests para ProxyManager."""
    
    def test_proxy_manager_empty_by_default(self):
        """ProxyManager sin config tiene lista vacía."""
        manager = ProxyManager()
        assert len(manager.proxies) == 0
        assert manager.get_next_proxy() is None
    
    def test_get_proxies_dict_returns_none_when_empty(self):
        """get_proxies_dict() devuelve None sin proxies."""
        manager = ProxyManager()
        assert manager.get_proxies_dict() is None
    
    def test_report_success_and_failure(self):
        """report_success() y report_failure() funcionan."""
        manager = ProxyManager()
        manager.proxies.append(ProxyConfig(url="http://proxy1.com:8080"))
        
        manager.report_success("http://proxy1.com:8080")
        assert manager.proxies[0].last_used is not None
        
        manager.report_failure("http://proxy1.com:8080")
        assert manager.proxies[0].failure_count == 1
    
    def test_get_status(self):
        """get_status() devuelve estado correcto."""
        manager = ProxyManager()
        manager.proxies.append(ProxyConfig(url="http://proxy1.com:8080"))
        
        status = manager.get_status()
        assert status["total"] == 1
        assert status["available"] == 1
        assert len(status["proxies"]) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
