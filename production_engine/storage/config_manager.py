"""
Config Manager - Persistent configuration with versioning
"""

import json
import os
from datetime import datetime
from typing import Dict, Any
import shutil

class ConfigManager:
    def __init__(self, data_dir: str = None):
        self.data_dir = data_dir or os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        self.config_file = os.path.join(self.data_dir, "config.json")
        self.versions_dir = os.path.join(self.data_dir, "config_versions")
        
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.versions_dir, exist_ok=True)
        
        self.config: Dict[str, Any] = {}
        
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r") as f:
                    self.config = json.load(f)
                print(f"✅ Config loaded from {self.config_file}")
            except Exception as e:
                print(f"⚠️ Error loading config: {e}")
                self.config = self._get_default_config()
        else:
            self.config = self._get_default_config()
            self.save_config()
            print(f"✅ Default config created")
            
        return self.config
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "starting_balance": 692.0,
            "budget_per_ai": 86.5,
            "trading_mode": "FUTURES",
            "direction": "SHORTS_ONLY",
            "max_leverage": 10,
            "pairs": ["BTC_USDT", "ETH_USDT", "SOL_USDT", "XRP_USDT", "AVAX_USDT"],
            "cold_wallet": os.getenv("COLD_WALLET_ADDRESS", ""),
            "withdraw_threshold": 100,
            "withdraw_chain": "TRC20",
            "risk_config": {
                "max_daily_loss_pct": 10,
                "max_total_loss_pct": 30,
                "protected_balance_pct": 70,
                "consecutive_loss_limit": 4
            },
            "rebalance_interval_hours": 4,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
    
    def save_config(self):
        """Save current configuration with versioning"""
        self.config["updated_at"] = datetime.now().isoformat()
        
        if os.path.exists(self.config_file):
            version_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            version_file = os.path.join(self.versions_dir, f"config_{version_id}.json")
            shutil.copy(self.config_file, version_file)
            
            self._cleanup_old_versions()
        
        with open(self.config_file, "w") as f:
            json.dump(self.config, f, indent=2)
            
        print(f"✅ Config saved")
    
    def _cleanup_old_versions(self, keep_count: int = 50):
        """Keep only recent config versions"""
        versions = sorted(os.listdir(self.versions_dir))
        if len(versions) > keep_count:
            for old_version in versions[:-keep_count]:
                os.remove(os.path.join(self.versions_dir, old_version))
    
    def update_config(self, updates: Dict[str, Any]):
        """Update configuration with new values"""
        self.config.update(updates)
        self.save_config()
    
    def rollback_to_version(self, version_id: str) -> bool:
        """Rollback to a specific config version"""
        version_file = os.path.join(self.versions_dir, f"config_{version_id}.json")
        
        if os.path.exists(version_file):
            shutil.copy(version_file, self.config_file)
            self.load_config()
            print(f"✅ Rolled back to version {version_id}")
            return True
        else:
            print(f"❌ Version {version_id} not found")
            return False
    
    def list_versions(self) -> list:
        """List all available config versions"""
        return sorted(os.listdir(self.versions_dir), reverse=True)
