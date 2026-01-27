import argparse
import sys
import os
from pathlib import Path
from typing import Dict, Any

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.config_loader import SimulationConfig
from simulation_runner import SimulationRunner

class OasisCLI:
    def __init__(self):
        self.parser = self._setup_argparse()
        
    def _setup_argparse(self):
        parser = argparse.ArgumentParser(
            description="🏠 Oasis 房产模拟系统 CLI",
            formatter_class=argparse.RawTextHelpFormatter
        )
        
        parser.add_argument('-i', '--interactive', action='store_true', help="启动交互式配置向导")
        
        # Override Parameters
        group = parser.add_argument_group('Simulation Parameters')
        group.add_argument('--agents', type=int, help="覆盖 Agent 数量")
        group.add_argument('--months', type=int, help="覆盖模拟时长 (月)")
        group.add_argument('--seed', type=int, help="设置随机种子 (复现结果)")
        
        # Config Selection
        config_group = parser.add_argument_group('Configuration')
        config_group.add_argument('--config', type=str, default="config/baseline.yaml", 
                                help="基础配置文件路径 (默认: config/baseline.yaml)")
        config_group.add_argument('--scenario', type=str, 
                                help="应用研究场景预设 (如: policy_restrictions)\n"
                                     "可选值: policy_restrictions, education_reform, \n"
                                     "        economic_crisis, baby_boom")

        return parser

    def list_scenarios(self) -> Dict[str, str]:
        """扫描 config/experiments 下的可用场景"""
        scenarios = {}
        exp_dir = Path("config/experiments")
        if exp_dir.exists():
            for f in exp_dir.glob("*.yaml"):
                scenarios[f.stem] = str(f)
        return scenarios

    def run_interactive_wizard(self) -> Dict[str, Any]:
        """交互式向导 - 引导用户配置模拟参数"""
        print("\n" + "="*60)
        print("   🏠 欢迎使用 Oasis 房产模拟系统")
        print("="*60 + "\n")
        
        args = {}
        
        # 1. 模式选择
        print("【步骤 1/4】选择运行模式:")
        print("  1. 基准模拟 (Baseline) - 使用默认的市场环境")
        print("  2. 研究场景 (Research) - 探索特定政策/事件影响")
        mode = input("\n请输入选项 [1/2，默认=1]: ").strip() or "1"
        
        baseline_path = "config/baseline.yaml"
        scenario_path = None
        
        if mode == "2":
            scenarios = self.list_scenarios()
            if not scenarios:
                print("\n❌ 未找到预设场景文件 (config/experiments/*.yaml)")
                print("   回退到基准模式\n")
            else:
                print("\n可用研究场景:")
                scenario_desc = {
                    "policy_restrictions": "限购限贷政策 - 模拟政府调控影响",
                    "education_reform": "学区房改革 - 探索教育资源均衡化",
                    "economic_crisis": "经济危机 - 失业率上升、收入下降",
                    "baby_boom": "婴儿潮 - 刚需激增、学区房溢价"
                }
                keys = list(scenarios.keys())
                for idx, key in enumerate(keys, 1):
                    desc = scenario_desc.get(key, "")
                    print(f"  {idx}. {key:20s} {desc}")
                
                s_input = input(f"\n请选择场景 [1-{len(keys)}，默认=1]: ").strip() or "1"
                try:
                    s_idx = int(s_input)
                    if 1 <= s_idx <= len(keys):
                        scenario_name = keys[s_idx-1]
                        scenario_path = scenarios[scenario_name]
                        print(f"✅ 已选择场景: {scenario_name}\n")
                    else:
                        print("❌ 无效选择，回退到基准模式\n")
                except:
                    print("❌ 输入错误，回退到基准模式\n")
        
        # 2. 参数配置
        print("【步骤 2/4】模拟规模配置 (直接回车使用默认值):")
        
        # Agent数量
        print("\n提示: Agent数量决定市场规模")
        print("  推荐值: 小规模测试=100, 中等规模=500, 大规模=1000+")
        a_input = input("Agent 数量 [默认=100]: ").strip()
        args['agents'] = int(a_input) if a_input else None
        
        # 月数
        print("\n提示: 模拟时长决定能观察到的市场演变")
        print("  推荐值: 快速验证=3, 观察趋势=12, 长期研究=24+")
        m_input = input("模拟月数 [默认=12]: ").strip()
        args['months'] = int(m_input) if m_input else None
        
        # 3. 高级选项
        print("\n【步骤 3/4】高级选项:")
        seed_choice = input("是否设置随机种子以复现结果? [y/N]: ").strip().lower()
        if seed_choice == 'y':
            s_input = input("  请输入种子值 (整数): ").strip()
            args['seed'] = int(s_input) if s_input else None
        else:
            args['seed'] = None
        
        args['config'] = baseline_path
        args['scenario_path'] = scenario_path
        
        # 4. 确认配置
        print("\n【步骤 4/4】配置确认:")
        print(f"  - 运行模式: {'研究场景' if scenario_path else '基准模拟'}")
        if scenario_path:
            print(f"  - 场景文件: {Path(scenario_path).stem}")
        print(f"  - Agent数量: {args['agents'] or '100 (默认)'}")
        print(f"  - 模拟月数: {args['months'] or '12 (默认)'}")
        print(f"  - 随机种子: {args['seed'] or '随机 (不可复现)'}")
        
        confirm = input("\n确认启动模拟? [Y/n]: ").strip().lower()
        if confirm == 'n':
            print("\n❌ 已取消模拟")
            return None
        
        print("\n" + "="*60)
        print("   🚀 配置完成，准备启动模拟...")
        print("="*60 + "\n")
        
        return args

    def main(self):
        args_namespace = self.parser.parse_args()
        
        params = {}
        config_path = args_namespace.config
        scenario_path = None
        
        # Decide mode
        if args_namespace.interactive:
            wizard_params = self.run_interactive_wizard()
            if not wizard_params:
                return
            
            params['agent_count'] = wizard_params['agents']
            params['months'] = wizard_params['months']
            params['seed'] = wizard_params['seed']
            config_path = wizard_params['config']
            scenario_path = wizard_params.get('scenario_path')
            
        else:
            # CLI Mode
            params['agent_count'] = args_namespace.agents
            params['months'] = args_namespace.months
            params['seed'] = args_namespace.seed
            
            if args_namespace.scenario:
                # Resolve scenario path
                # Try simple name first
                possible_path = Path("config/experiments") / f"{args_namespace.scenario}.yaml"
                if possible_path.exists():
                    scenario_path = str(possible_path)
                elif Path(args_namespace.scenario).exists():
                     scenario_path = args_namespace.scenario
                else:
                    print(f"❌ 找不到场景配置: {args_namespace.scenario}")
                    sys.exit(1)

        # 1. Load Baseline Config
        print(f"\n⚙️  Loading Config: {config_path}")
        config = SimulationConfig(config_path)
        
        # 2. Apply Scenario Override (if any)
        if scenario_path:
            print(f"🔬 Applying Scenario: {scenario_path}")
            # SimulationConfig doesn't have a direct merge mostly because it's simple
            # But we can instantiate a second one and manually update?
            # Better: Make SimulationConfig support loading multiple or merging.
            # For now, let's simply load the scenario yaml and update the dict
            import yaml
            with open(scenario_path, 'r', encoding='utf-8') as f:
                scenario_data = yaml.safe_load(f)
            
            # Recursive update helper
            def deep_update(d, u):
                for k, v in u.items():
                    if isinstance(v, dict):
                        d[k] = deep_update(d.get(k, {}), v)
                    else:
                        d[k] = v
                return d
            
            deep_update(config._config, scenario_data)
        
        # 3. Create Runner
        runner = SimulationRunner(
            agent_count=params.get('agent_count'),
            months=params.get('months'),
            seed=params.get('seed'),
            config=config
        )
        
        # 4. Run
        print("\n🚀 Starting Simulation...")
        runner.run()

if __name__ == "__main__":
    cli = OasisCLI()
    cli.main()
