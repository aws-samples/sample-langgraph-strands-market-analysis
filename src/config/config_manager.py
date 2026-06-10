"""
Configuration Manager for Market Surveillance AgentCore Deployment

Manages static and dynamic configuration files for the application.
"""

import os
import yaml
from typing import Dict, Any


class ConfigManager:
    """Manages configuration files for Market Surveillance deployment"""
    
    def __init__(self, config_dir: str = None):
        """
        Initialize configuration manager
        
        Args:
            config_dir: Directory containing config files. Defaults to './config'
        """
        if config_dir is None:
            # src/config/config_manager.py -> go up two levels to reach the project root
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            config_dir = os.path.join(project_root, 'config')
        
        self.config_dir = config_dir
        self.static_config_path = os.path.join(config_dir, 'static-config.yaml')
        self.dynamic_config_path = os.path.join(config_dir, 'dynamic-config.yaml')
    
    def _load_yaml(self, file_path: str) -> Dict[str, Any]:
        """Load YAML file and return as dictionary"""
        try:
            with open(file_path, 'r') as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            print(f"Warning: Config file not found: {file_path}")
            return {}
        except Exception as e:
            print(f"Error loading config file {file_path}: {e}")
            return {}
    
    def _save_yaml(self, data: Dict[str, Any], file_path: str):
        """Save dictionary to YAML file"""
        try:
            with open(file_path, 'w') as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        except Exception as e:
            raise Exception(f"Error saving config file {file_path}: {e}")
    
    def get_static_config(self) -> Dict[str, Any]:
        """Get static configuration"""
        return self._load_yaml(self.static_config_path)
    
    def get_dynamic_config(self) -> Dict[str, Any]:
        """Get dynamic configuration"""
        return self._load_yaml(self.dynamic_config_path)
    
    def get_merged_config(self) -> Dict[str, Any]:
        """
        Get merged configuration (static + dynamic)
        Dynamic values override static values
        """
        static = self.get_static_config()
        dynamic = self.get_dynamic_config()
        
        # Deep merge
        merged = self._deep_merge(static, dynamic)
        return merged
    
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries"""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def update_dynamic_config(self, updates: Dict[str, Any]):
        """
        Update dynamic configuration file with new values
        
        Args:
            updates: Dictionary of values to update
        """
        # Load current dynamic config
        current = self.get_dynamic_config()
        
        # Merge updates
        updated = self._deep_merge(current, updates)
        
        # Save back to file
        self._save_yaml(updated, self.dynamic_config_path)
    
    def get_runtime_arn(self) -> str:
        """Get the runtime ARN from dynamic config"""
        config = self.get_dynamic_config()
        return config.get('runtime', {}).get('arn', '')
    
    def get_ecr_uri(self) -> str:
        """Get the ECR URI from dynamic config"""
        config = self.get_dynamic_config()
        return config.get('runtime', {}).get('ecr_uri', '')