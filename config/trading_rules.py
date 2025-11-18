"""
Trading Configuration Loader
Loads and validates trading configuration from YAML files
"""

import yaml
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class TradingConfig:
    """Typed trading configuration"""
    # Core settings
    loop_interval: float = 0.5
    close_positions_on_shutdown: bool = True
    
    # Exchange settings
    exchange: Dict[str, Any] = field(default_factory=dict)
    
    # Strategy settings
    strategies: Dict[str, Any] = field(default_factory=dict)
    
    # Risk management
    risk: Dict[str, Any] = field(default_factory=dict)
    
    # Execution settings
    execution: Dict[str, Any] = field(default_factory=dict)
    
    # Monitoring settings
    monitoring: Dict[str, Any] = field(default_factory=dict)

async def load_trading_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Load trading configuration from YAML file
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Configuration dictionary
        
    Raises:
        FileNotFoundError: If config file not found
        yaml.YAMLError: If config file is invalid
    """
    if config_path is None:
        config_path = Path('config/trading_rules.yml')
    
    try:
        logger.info(f"Loading trading configuration from {config_path}")
        
        if not config_path.exists():
            # Create default config if it doesn't exist
            await _create_default_config(config_path)
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Validate configuration
        validated_config = await _validate_config(config)
        
        logger.info("✅ Trading configuration loaded and validated")
        return validated_config
        
    except FileNotFoundError:
        logger.error(f"❌ Configuration file not found: {config_path}")
        raise
    except yaml.YAMLError as e:
        logger.error(f"❌ Invalid YAML configuration: {e}")
        raise
    except Exception as e:
        logger.error(f"❌ Failed to load configuration: {e}")
        raise

async def _validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and normalize configuration
    
    Args:
        config: Raw configuration dictionary
        
    Returns:
        Validated and normalized configuration
    """
    # Set defaults for missing values
    defaults = {
        'loop_interval': 0.5,
        'close_positions_on_shutdown': True,
        'exchange': {
            'symbol': 'SOL-USD',
            'testnet': False,
            'max_reconnect_attempts': 10
        },
        'account': {
            'max_leverage': 5,
            'max_daily_loss': 0.05,
            'margin_threshold': 0.8
        },
        'risk': {
            'max_drawdown': 0.15,
            'consecutive_loss_limit': 5,
            'volatility_threshold': 0.05
        },
        'execution': {
            'default_slippage_limit': 0.005,
            'max_order_attempts': 3,
            'order_timeout': 30
        },
        'logging': {
            'level': 'INFO',
            'console_output': True,
            'file_output': True
        }
    }
    
    # Merge defaults with provided config
    validated_config = _deep_merge_dicts(defaults, config)
    
    # Validate critical settings
    await _validate_critical_settings(validated_config)
    
    return validated_config

def _deep_merge_dicts(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge two dictionaries"""
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge_dicts(result[key], value)
        else:
            result[key] = value
    
    return result

async def _validate_critical_settings(config: Dict[str, Any]) -> None:
    """Validate critical configuration settings"""
    
    # Validate loop interval
    loop_interval = config.get('loop_interval', 0.5)
    if not isinstance(loop_interval, (int, float)) or loop_interval <= 0:
        raise ValueError("loop_interval must be a positive number")
    
    # Validate risk settings
    risk_config = config.get('risk', {})
    
    max_drawdown = risk_config.get('max_drawdown', 0.15)
    if not 0 < max_drawdown < 1:
        raise ValueError("max_drawdown must be between 0 and 1")
    
    # Validate position sizing
    position_config = config.get('position_sizing', {})
    
    max_position_size = position_config.get('max_position_size', 0.1)
    if not 0 < max_position_size <= 1:
        raise ValueError("max_position_size must be between 0 and 1")
    
    # Validate strategy settings
    strategies = config.get('strategies', {})
    if not strategies:
        logger.warning("⚠️ No trading strategies configured")
    
    logger.debug("✅ Critical settings validation passed")

async def _create_default_config(config_path: Path) -> None:
    """Create default configuration file"""
    default_config = {
        'loop_interval': 0.5,
        'close_positions_on_shutdown': True,
        'exchange': {
            'symbol': 'SOL-USD',
            'testnet': True,  # Default to testnet for safety
            'max_reconnect_attempts': 10
        },
        'account': {
            'max_leverage': 5,
            'max_daily_loss': 0.05,
            'margin_threshold': 0.8
        },
        'risk': {
            'max_drawdown': 0.15,
            'consecutive_loss_limit': 5,
            'volatility_threshold': 0.05
        },
        'scalping_v1': {
            'enabled': True,
            'rsi_period': 14,
            'ema_fast': 9,
            'ema_slow': 21,
            'take_profit_pct': 0.015,
            'stop_loss_pct': 0.007
        },
        'logging': {
            'level': 'INFO',
            'console_output': True,
            'file_output': True
        }
    }
    
    # Ensure directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(config_path, 'w') as f:
        yaml.dump(default_config, f, default_flow_style=False, indent=2)
    
    logger.info(f"📝 Created default configuration at {config_path}")

def get_strategy_config(config: Dict[str, Any], strategy_name: str) -> Dict[str, Any]:
    """Get configuration for a specific strategy"""
    return config.get(strategy_name, {})

def get_risk_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Get risk management configuration"""
    return config.get('risk', {})

def get_execution_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Get execution configuration"""
    return config.get('execution', {})

def update_config_value(config: Dict[str, Any], key_path: str, value: Any) -> Dict[str, Any]:
    """
    Update a configuration value using dot notation
    
    Args:
        config: Configuration dictionary
        key_path: Dot-separated key path (e.g., 'risk.max_drawdown')
        value: New value
        
    Returns:
        Updated configuration dictionary
    """
    keys = key_path.split('.')
    current = config
    
    # Navigate to the parent of the target key
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    
    # Set the value
    current[keys[-1]] = value
    
    return config

if __name__ == "__main__":
    import asyncio
    
    async def test_config_loading():
        """Test configuration loading"""
        try:
            config = await load_trading_config()
            print("✅ Configuration loaded successfully")
            print(f"Loop interval: {config.get('loop_interval')}")
            print(f"Target symbol: {config.get('exchange', {}).get('symbol')}")
            print(f"Max drawdown: {config.get('risk', {}).get('max_drawdown')}")
        except Exception as e:
            print(f"❌ Configuration test failed: {e}")
    
    asyncio.run(test_config_loading())