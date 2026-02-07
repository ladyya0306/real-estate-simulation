#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Oasis Real Estate Simulation Runner (v2.2 Scholar Edition)
增强版：完整的交互式参数配置，包含收入档次、房产分配、市场健康检查
"""
import sys
import logging
import random
import numpy as np
import os
from pathlib import Path
from config.config_loader import SimulationConfig
from simulation_runner import SimulationRunner

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)

def input_default(prompt, default_value):
    """Helper for input with default value"""
    val = input(f"{prompt} [default: {default_value}]: ").strip()
    return val if val else str(default_value)

def validate_config(agent_config, property_count):
    """
    市场健康检查：验证配置是否可能导致0交易
    
    Returns:
        (is_valid, warnings, errors)
    """
    warnings = []
    errors = []
    
    # 1. 检查房产总数是否足够
    total_properties_needed = sum(tier['property_count'][1] for tier in agent_config.values())
    if property_count < total_properties_needed:
        errors.append(f"🔴 严重: 房产总数({property_count}) < 各档次房产数之和({total_properties_needed})")
        errors.append(f"   最少需要 {total_properties_needed} 套房产")
    
    # 2. 检查收入分布（低收入人群不应过多）
    total_agents = sum(tier['count'] for tier in agent_config.values())
    low_income_count = agent_config['low']['count'] + agent_config['low_mid']['count']
    low_income_ratio = low_income_count / total_agents
    
    if low_income_ratio > 0.7:
        warnings.append(f"🟡 提示: 低收入人群占比 {low_income_ratio:.1%} 过高")
        warnings.append(f"   可能导致大部分Agent买不起房产，建议控制在60%以下")
    
    # 3. 检查房产分配的合理性
    avg_properties_per_person = property_count / total_agents
    if avg_properties_per_person < 0.5:
        warnings.append(f"🟡 提示: 人均房产数 {avg_properties_per_person:.2f} 偏低")
        warnings.append(f"   可能导致市场房源不足，建议至少0.8套/人")
    
    # 4. 估算可负担性（粗略）
    # 假设中高收入人群能买得起房
    potential_buyers = (agent_config['middle']['count'] + 
                       agent_config['high']['count'] + 
                       agent_config['ultra_high']['count'])
    buyer_ratio = potential_buyers / total_agents
    
    if buyer_ratio < 0.3:
        warnings.append(f"🟡 提示: 潜在买家占比 {buyer_ratio:.1%} 偏低")
        warnings.append(f"   建议中高收入群体至少占30%")
    
    return (len(errors) == 0, warnings, errors)

def main():
    # UTF-8
    try:
        if sys.stdout.encoding != 'utf-8':
            sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

    print("\n" + "=" * 60)
    print("     🏠 Oasis Real Estate Sandbox (Scholar Edition v2.2)     ".center(60))
    print("=" * 60)
    
    # --- 1. Seed Control ---
    seed_val = input_default("Enter Random Seed (for reproducibility)", "random")
    seed_to_use = None
    if seed_val != "random":
        try:
            seed_int = int(seed_val)
            seed_to_use = seed_int
            random.seed(seed_int)
            np.random.seed(seed_int)
            print(f"✅ Random Seed set to: {seed_int}")
        except ValueError:
            print("⚠️ Invalid seed, using random.")
            logging.info("使用随机种子 (结果不可复现)")
    else:
        logging.info("使用随机种子 (结果不可复现)")
    
    # --- 2. Mode Selection ---
    print("\nSelect Mode:")
    print("1. Start NEW Simulation (Wipe previous data)")
    print("2. RESUME Simulation (Load from DB)")
    mode = input_default("Choose option", "1")
    
    resume = False
    
    if mode == "2":
        resume = True
        print("📂 Select a project to RESUME:")
        import project_manager
        projects = project_manager.list_projects()
        
        if not projects:
            print("❌ No projects found to resume.")
            return
            
        for i, p in enumerate(projects):
            print(f"  {i+1}. {os.path.basename(p)}")
            
        idx = int(input_default("Select project (0 to cancel)", "1")) - 1
        if idx < 0: return
        
        if 0 <= idx < len(projects):
            selected_proj = projects[idx]
            config_path, db_path = project_manager.load_project_paths(selected_proj)
            print(f"✅ Loading project: {selected_proj}")
            
            # Load config from project
            config = SimulationConfig(config_path)
            months = int(input_default("How many MORE months to simulate?", "12"))
        else:
            print("❌ Invalid selection.")
            return

    else:
        # NEW Simulation
        pass
        # Remove old DB handled by project_manager logic (new folder)

        # Remove old DB handled by project_manager logic (new folder)
        # try-except block removed as it was orphaned

        print("\n" + "=" * 60)
        print("--- Configuration ---")
        print("=" * 60)
        use_custom = input_default("Use Custom Parameters? (y/N)", "n")
        
        if use_custom.lower() != 'y':
            # 使用默认配置
            print("✅ Using Default Parameters.")
            
            # [Fix] Also create project folder for default config
            import project_manager
            proj_dir, config_path, db_path = project_manager.create_new_project("config/baseline.yaml")
            print(f"✅ Created New Project at: {proj_dir}")
            
            config = SimulationConfig(config_path)
            
            agent_count = 100
            months = 12
            
            if seed_to_use is not None:
                config.update('simulation.random_seed', seed_to_use)
            config.save()
        else:
            print("\n⚠️  注意: 以下参数将直接影响市场流动性和交易活跃度")
            print("   不当配置可能导致0交易，请参考默认值谨慎设置\n")
            
            # === Agent 配置 ===
            print("=" * 60)
            print("【步骤 1/4】Agent 数量与收入档次配置")
            print("=" * 60)
            
            # Agent总数
            agent_count = int(input_default("\n总Agent数量", "100"))
            
            # 收入档次配置
            print("\n📊 收入档次配置 (共5档):")
            print("   提示: 收入分界线单位为 元/月")
            print("   参考: 低收入<20k, 中低收入20-40k, 中等收入40-80k, 高收入80-150k, 超高收入>150k\n")
            
            # 默认收入分界线
            default_income_bounds = {
                'ultra_high': (150000, 300000),
                'high': (80000, 150000),
                'middle': (40000, 80000),
                'low_mid': (20000, 40000),
                'low': (8000, 20000)
            }
            
            agent_config = {}
            total_assigned = 0
            
            for tier_key in ['ultra_high', 'high', 'middle', 'low_mid', 'low']:
                tier_names = {
                    'ultra_high': '超高收入',
                    'high': '高收入',
                    'middle': '中等收入',
                    'low_mid': '中低收入',
                    'low': '低收入'
                }
                
                default_bounds = default_income_bounds[tier_key]
                print(f"\n【{tier_names[tier_key]}档】")
                print(f"  默认收入范围: {default_bounds[0]:,} - {default_bounds[1]:,} 元/月")
                
                # 该档次人数
                remaining = agent_count - total_assigned
                if tier_key == 'low':
                    # 最后一档自动分配剩余
                    count = remaining
                    print(f"  该档Agent数量: {count} (剩余自动分配)")
                else:
                    default_count = {
                        'ultra_high': max(1, agent_count // 20),  # 5%
               'high': max(2, agent_count // 10),   # 10%
                        'middle': max(5, agent_count // 2),    # 50%
                        'low_mid': max(2, agent_count // 5)    # 20%
                    }.get(tier_key, 1)
                    count = int(input_default(f"  该档Agent数量", str(min(default_count, remaining))))
                
                total_assigned += count
                
                # 该档次房产数范围
                default_props = {
                    'ultra_high': (2, 5),
                    'high': (1, 3),
                    'middle': (0, 1),
                    'low_mid': (0, 1),
                    'low': (0, 0)
                }[tier_key]
                
                props_min = int(input_default(f"  该档人均房产数(最小)", str(default_props[0])))
                props_max = int(input_default(f"  该档人均房产数(最大)", str(default_props[1])))
                
                agent_config[tier_key] = {
                    'count': count,
                    'income_range': default_bounds,
                    'property_count': (props_min, props_max)
                }
            
            # === 房产配置 ===
            print("\n" + "=" * 60)
            print("【步骤 2/4】房产总量配置")
            print("=" * 60)
            
            min_properties = sum(tier['property_count'][0] * tier['count'] 
                               for tier in agent_config.values())
            max_properties = sum(tier['property_count'][1] * tier['count'] 
                               for tier in agent_config.values())
            
            print(f"\n根据配置，至少需要 {min_properties} 套房产")
            print(f"最多需要 {max_properties} 套房产")
            print(f"建议: {int(max_properties * 1.2)} 套 (留20%市场库存)\n")
            
            property_count = int(input_default("房产总数量", str(int(max_properties * 1.2))))
            
            # === 市场健康检查 ===
            print("\n" + "=" * 60)
            print("【步骤 3/4】市场健康检查")
            print("=" * 60)
            
            is_valid, warnings, errors = validate_config(agent_config, property_count)
            
            if errors:
                print("\n❌ 配置错误:")
                for err in errors:
                    print(f"  {err}")
                print("\n请修正后重新运行。")
                return
            
            if warnings:
                print("\n⚠️  配置警告:")
                for warn in warnings:
                    print(f"  {warn}")
                print("\n这些配置可能导致交易不活跃，但可以继续运行。")
                confirm = input("\n是否继续? [Y/n]: ").strip().lower()
                if confirm == 'n':
                    print("已取消模拟。")
                    return
            else:
                print("\n✅ 配置检查通过！")
            
            # === 最终确认 ===
            print("\n" + "=" * 60)
            print("【步骤 4/4】配置总览与确认")
            print("=" * 60)
            
            months = int(input_default("\n模拟月数", "12"))
            
            print(f"\n配置总览:")
            print(f"  - Agent总数: {agent_count}")
            for tier_key, tier_data in agent_config.items():
                tier_names = {'ultra_high': '超高', 'high': '高', 'middle': '中', 'low_mid': '中低', 'low': '低'}
                print(f"      {tier_names[tier_key]}收入: {tier_data['count']}人, "
                      f"收入{tier_data['income_range'][0]//1000}-{tier_data['income_range'][1]//1000}k, "
                      f"拥房{tier_data['property_count'][0]}-{tier_data['property_count'][1]}套")
            print(f"  - 房产总数: {property_count}")
            print(f"  - 模拟月数: {months}")
            print(f"  - 随机种子: {seed_to_use or '随机'}")
            
            confirm = input("\n确认启动模拟? [Y/n]: ").strip().lower()
            if confirm == 'n':
                print("已取消模拟。")
                return
            
            # === 创建项目文件夹 ===
            import project_manager
            proj_dir, config_path, db_path = project_manager.create_new_project("config/baseline.yaml")
            print(f"✅ Created New Project at: {proj_dir}")
            
            # 重新加载新位置的配置
            config = SimulationConfig(config_path)
            
            # 更新配置并保存到项目目录
            if seed_to_use is not None:
                config.update('simulation.random_seed', seed_to_use)
            
            # 保存用户自定义参数
            if 'agent_config' in locals() and agent_config:
                config._config['user_agent_config'] = agent_config
            if 'property_count' in locals():
                config._config['user_property_count'] = property_count
                
            config.save()

    # --- 3. Execution ---
    print("\n🚀 Initializing Runner...")
    
    runner = SimulationRunner(
        agent_count=agent_count if not resume else 0,
        months=months,
        seed=seed_to_use,
        resume=resume,
        config=config,
        db_path=db_path
    )
    
    try:
        runner.run()
        print("\n✅ Simulation Completed Successfully.")
        
        # --- 4. Auto Export ---
        print("\n📦 Exporting Results...")
        try:
            import scripts.export_results as exporter
            # Pass correct paths to exporter
            output_dir = os.path.dirname(db_path)
            exporter.export_data(db_path=db_path, output_dir=output_dir)
        except ImportError:
            import subprocess
            subprocess.run([sys.executable, "scripts/export_results.py"])
            
    except KeyboardInterrupt:
        print("\n🛑 Simulation Stopped by User.")
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
