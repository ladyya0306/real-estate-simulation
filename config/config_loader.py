import yaml
from pathlib import Path
from typing import Dict, Any, Optional

class SimulationConfig:
    """
    统一配置加载器
    负责读取 config/baseline.yaml 及其覆盖配置
    提供属性访问方式 (如 config.simulation.agent_count)
    """
    
    def __init__(self, config_path: str = "config/baseline.yaml"):
        # 兼容绝对路径和相对路径
        if Path(config_path).is_absolute():
            self.config_path = Path(config_path)
        else:
             # 假设相对路径是相对于项目根目录 (此处简单处理，可根据需要增强)
            # 在实际运行中，通常CWD就是项目根目录
            self.config_path = Path(config_path)

        self._config: Dict[str, Any] = {}
        self.load()
    
    def load(self):
        """加载YAML配置"""
        if not self.config_path.exists():
            # 尝试在当前目录查找 (容错)
            local_path = Path.cwd() / self.config_path
            if local_path.exists():
                self.config_path = local_path
            else:
                raise FileNotFoundError(f"配置文件不存在: {self.config_path}")
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f)
        except Exception as e:
            raise RuntimeError(f"无法解析配置文件 {self.config_path}: {str(e)}")

    def get(self, key_path: str, default=None):
        """
        获取配置值，支持点号路径
        例如: config.get('market.zones.A.base_price_per_sqm')
        """
        keys = key_path.split('.')
        value = self._config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def update(self, key_path: str, value: Any):
        """
        更新配置值 (用于参数覆盖)
        """
        keys = key_path.split('.')
        target = self._config
        
        for key in keys[:-1]:
            target = target.setdefault(key, {})
        
        target[keys[-1]] = value

    # ====== 便捷访问属性 ======
    @property
    def simulation(self) -> Dict: return self._config.get('simulation', {})
    
    @property
    def market(self) -> Dict: return self._config.get('market', {})
    
    @property
    def agent_tiers(self) -> Dict: return self._config.get('agent_tiers', {})
    
    @property
    def property_allocation(self) -> Dict: return self._config.get('property_allocation', {})

    @property
    def decision_factors(self) -> Dict: return self._config.get('decision_factors', {})
    
    @property
    def mortgage(self) -> Dict: return self._config.get('mortgage', {})
    
    @property
    def macro_environment(self) -> Dict: return self._config.get('macro_environment', {})

    @property
    def negotiation(self) -> Dict: return self._config.get('negotiation', {})

    @property
    def system(self) -> Dict: return self._config.get('system', {})
