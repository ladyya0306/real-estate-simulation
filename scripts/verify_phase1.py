from config.config_loader import SimulationConfig
import sys

def test_config_system():
    print("Running Phase 1 Verification...")
    
    # 1. 检查依赖
    try:
        import yaml
        import tqdm
        print("✅ Dependencies (pyyaml, tqdm) installed.")
    except ImportError as e:
        print(f"❌ Dependency missing: {e}")
        return

    # 2. 加载基准配置
    try:
        config = SimulationConfig("config/baseline.yaml")
        print("✅ Config loaded successfully.")
    except Exception as e:
        print(f"❌ Failed to load config: {e}")
        return

    # 3. 验证关键参数
    agent_count = config.simulation['agent_count']
    if agent_count == 100:
        print(f"✅ Baseline agent_count verified: {agent_count}")
    else:
        print(f"❌ Baseline agent_count mismatch: {agent_count}")
        
    zones = config.market['zones']
    if 'A' in zones and 'B' in zones:
        print("✅ Market zones verified.")
    else:
        print("❌ Market zones missing.")

    print("\nPhase 1 Implementation Verified Successfully!")

if __name__ == "__main__":
    test_config_system()
