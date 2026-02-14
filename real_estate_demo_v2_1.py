#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Oasis Real Estate Simulation Runner (v2.2 Scholar Edition)
增强版：完整的交互式参数配置，包含收入档次、房产分配、市场健康检查
"""
import logging
import os
import random
import subprocess
import sys

import numpy as np

from config.config_loader import SimulationConfig
from simulation_runner import SimulationRunner


# ✅ LoggerWriter for Tee Logging (Console + File)
# Uses the FileHandler from logging to avoid file locking issues on Windows
class LoggerWriter:
    def __init__(self, writer, file_stream=None):
        self.writer = writer
        self.file_stream = file_stream

    def write(self, message):
        self.writer.write(message)
        if self.file_stream:
            try:
                self.file_stream.write(message)
                self.file_stream.flush()  # Ensure it hits disk
            except BaseException:
                pass

    def flush(self):
        self.writer.flush()
        if self.file_stream:
            try:
                self.file_stream.flush()
            except BaseException:
                pass


# Configure logging first (via SimulationRunner import or explicit config check)
# Since SimulationRunner import configures logging, we can inspect handlers
log_file_stream = None
root_logger = logging.getLogger()
for h in root_logger.handlers:
    if isinstance(h, logging.FileHandler):
        log_file_stream = h.stream
        break

# If no file handler found (e.g. import didn't run it), configure it manually fallback
if not log_file_stream:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        encoding='utf-8',
        handlers=[
            logging.FileHandler("simulation_run.log", encoding='utf-8', mode='w'),
            logging.StreamHandler()
        ]
    )
    for h in logging.getLogger().handlers:
        if isinstance(h, logging.FileHandler):
            log_file_stream = h.stream
            break

# Redirect stdout/stderr
sys.stdout = LoggerWriter(sys.stdout, log_file_stream)
sys.stderr = LoggerWriter(sys.stderr, log_file_stream)


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
        warnings.append("   可能导致大部分Agent买不起房产，建议控制在60%以下")

    # 3. 检查房产分配的合理性
    avg_properties_per_person = property_count / total_agents
    if avg_properties_per_person < 0.5:
        warnings.append(f"🟡 提示: 人均房产数 {avg_properties_per_person:.2f} 偏低")
        warnings.append("   可能导致市场房源不足，建议至少0.8套/人")

    # 4. 估算可负担性（粗略）
    # 假设中高收入人群能买得起房
    potential_buyers = (agent_config['middle']['count'] +
                        agent_config['high']['count'] +
                        agent_config['ultra_high']['count'])
    buyer_ratio = potential_buyers / total_agents

    if buyer_ratio < 0.3:
        warnings.append(f"🟡 提示: 潜在买家占比 {buyer_ratio:.1%} 偏低")
        warnings.append("   建议中高收入群体至少占30%")

    return (len(errors) == 0, warnings, errors)


def show_intervention_menu(runner):
    """
    显示研究员干预面板
    """
    print("\n" + "=" * 50)
    print("🔬 研究员干预面板 (Researcher Intervention Panel)")
    print("=" * 50)
    print("通过调整以下参数，模拟不同的宏观经济环境。")
    print("📉 消极影响: 降薪、失业、加息 -> 抑制需求")
    print("📈 积极影响: 人口流入、降息、增供 -> 刺激交易")

    interventions = []

    while True:
        print("\n--- 干预选项 ---")
        print("1. [劳动力] 薪资调整 (Wage Shock)")
        print("2. [劳动力] 失业潮 (Unemployment Shock)")
        print("3. [人口] 新增人口 (Migration In)")
        print("4. [人口] 移除人口 (Migration Out)")
        print("5. [房产] 新增房源 (New Supply)")
        print("6. [房产] 下架房源 (Supply Cut)")
        print("0. ✅ 执行策略并继续 (Execute)")

        choice = input("Select option [0-6]: ").strip()

        try:
            if choice == '0':
                if interventions:
                    runner.set_interventions(interventions)
                    print(f"✅ 已提交 {len(interventions)} 项干预措施给公告栏。")
                break

            elif choice == '1':
                val = input("调整幅度 (e.g. -0.1 for -10%, 0.1 for +10%): ").strip()
                if not val:
                    continue
                pct = float(val)
                tier = input_default("覆盖阶层 (all/low/middle/high...)", "all")
                count = runner.intervention_service.apply_wage_shock(runner.agent_service, pct, tier)
                msg = f"Policy: Wage adjusted by {pct * 100:+.1f}% for {tier} tier."
                interventions.append(msg)
                print(f"✅ {msg}")

            elif choice == '2':
                val = input("失业率 (e.g. 0.2 for 20%): ").strip()
                if not val:
                    continue
                rate = float(val)
                tier = input_default("目标阶层 (low/middle...)", "low")
                count = runner.intervention_service.apply_unemployment_shock(runner.agent_service, rate, tier)
                msg = f"Policy: Unemployment shock of {rate * 100:.1f}% hit {tier} tier ({count} affected)."
                interventions.append(msg)
                print(f"✅ {msg}")

            elif choice == '3':
                val = input("新增数量: ").strip()
                if not val:
                    continue
                count = int(val)
                tier = input_default("阶层 (low/middle/high...)", "middle")
                added = runner.intervention_service.add_population(runner.agent_service, count, tier)
                msg = f"Demographics: {added} new {tier} income agents entered the city."
                interventions.append(msg)
                print(f"✅ {msg}")

            elif choice == '4':
                val = input("移除数量: ").strip()
                if not val:
                    continue
                count = int(val)
                tier = input_default("阶层 (low/middle/high...)", "low")
                removed = runner.intervention_service.remove_population(runner.agent_service, count, tier)
                msg = f"Demographics: {removed} {tier} income agents left the city."
                interventions.append(msg)
                print(f"✅ {msg}")

            elif choice == '5':
                val = input("新增房源数: ").strip()
                if not val:
                    continue
                count = int(val)
                zone = input_default("区域 (A/B)", "A")
                runner.intervention_service.adjust_housing_supply(runner.market_service, count, zone)
                msg = f"Supply: {count} new properties released in Zone {zone}."
                interventions.append(msg)
                print(f"✅ {msg}")

            elif choice == '6':
                val = input("下架房源数: ").strip()
                if not val:
                    continue
                count = int(val)
                zone = input_default("区域 (A/B)", "A")
                removed = runner.intervention_service.supply_cut(runner.market_service, count, zone)
                msg = f"Supply: {removed} listings removed from Zone {zone}."
                interventions.append(msg)
                print(f"✅ {msg}")

            else:
                print("❌ Invalid option.")

        except Exception as e:
            print(f"❌ Error executing intervention: {e}")
            import traceback
            traceback.print_exc()


def run_forensic_analysis_menu():
    """
    运行逻辑体检 (Forensic Analysis) 菜单
    """
    print("\n" + "=" * 60)
    print("🕵️  逻辑体检与法医分析 (Forensic Analysis)".center(60))
    print("=" * 60)

    # Select Project
    import project_manager
    print("📂 请选择要分析的项目:")
    projects = project_manager.list_projects()

    if not projects:
        print("❌ 未找到任何项目。")
        return

    for i, p in enumerate(projects):
        print(f"  {i + 1}. {os.path.basename(p)}")

    idx_str = input_default("选择项目 (0返回)", "1")
    if not idx_str.isdigit():
        return
    idx = int(idx_str) - 1
    if idx < 0:
        return

    if 0 <= idx < len(projects):
        selected_proj = projects[idx]
        _, db_path = project_manager.load_project_paths(selected_proj)

        if not os.path.exists(db_path):
            print(f"❌ 数据库文件不存在: {db_path}")
            return

        print(f"✅ 已选中数据库: {db_path}")

        while True:
            print("\n--- 分析模式 ---")
            print("A. 批量全面扫描 (Batch Check) - 快速找出逻辑硬伤")
            print("B. 单人深度画像 (Single Profile) - 生成时序逻辑报告")
            print("0. 返回主菜单")

            mode = input("请选择模式 [A/B/0]: ").strip().upper()

            if mode == '0':
                break

            cmd = [sys.executable, "generate_enhanced_diaries.py", "--db", db_path]

            if mode == 'A':
                cmd.extend(["--mode", "batch"])
                subprocess.run(cmd)

            elif mode == 'B':
                cmd.extend(["--mode", "single"])
                aid = input("请输入 Agent ID: ").strip()
                if aid:
                    cmd.extend(["--agent_id", aid])
                    subprocess.run(cmd)
            else:
                print("❌ 无效选项")
    else:
        print("❌ 无效选择")


def main():
    # UTF-8
    try:
        if sys.stdout.encoding != 'utf-8':
            sys.stdout.reconfigure(encoding='utf-8')
    except BaseException:
        pass

    while True:
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
        print("3. 运行逻辑体检 (Forensic Analysis)")
        print("0. Exit")

        mode = input_default("Choose option", "1")

        if mode == '0':
            print("Bye!")
            break

        if mode == '3':
            run_forensic_analysis_menu()
            continue

        resume = False

        if mode == "2":
            resume = True
            print("📂 Select a project to RESUME:")
            import project_manager
            projects = project_manager.list_projects()

            if not projects:
                print("❌ No projects found to resume.")
                continue  # Loop back

            for i, p in enumerate(projects):
                print(f"  {i + 1}. {os.path.basename(p)}")

            idx = int(input_default("Select project (0 to cancel)", "1")) - 1
            if idx < 0:
                continue

            if 0 <= idx < len(projects):
                selected_proj = projects[idx]
                config_path, db_path = project_manager.load_project_paths(selected_proj)
                print(f"✅ Loading project: {selected_proj}")

                # Load config from project
                config = SimulationConfig(config_path)
                months = int(input_default("How many MORE months to simulate?", "12"))
            else:
                print("❌ Invalid selection.")
                continue

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
                        count = int(input_default("  该档Agent数量", str(min(default_count, remaining))))

                    total_assigned += count

                    # 该档次房产数范围
                    default_props = {
                        'ultra_high': (2, 5),
                        'high': (1, 3),
                        'middle': (0, 1),
                        'low_mid': (0, 1),
                        'low': (0, 0)
                    }[tier_key]

                    props_min = int(input_default("  该档人均房产数(最小)", str(default_props[0])))
                    props_max = int(input_default("  该档人均房产数(最大)", str(default_props[1])))

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

                # 🆕 === 区域单价配置 ===
                print("\n" + "=" * 60)
                print("【步骤 2.5/4】区域房价配置 (单价)")
                print("=" * 60)

                print("\n💰 区域单价配置 (¥/㎡)")
                print("   说明: 配置后，房产价格 = 单价 × 建筑面积")
                print("   参考: 一线城市核心区3-5万/㎡，非核心区1-2万/㎡\n")

                zone_price_config = {}
                # [Fix] Create temp config to read defaults (since project config doesn't exist yet)
                temp_config = SimulationConfig("config/baseline.yaml")

                for zone, zone_name in [('A', '核心区'), ('B', '非核心区')]:
                    # 从配置文件获取默认值
                    default_range = temp_config.get_zone_price_range(zone)
                    default_min = default_range['min']
                    default_max = default_range['max']

                    print(f"【{zone}区 - {zone_name}】")
                    print(f"  当前默认单价: {default_min:,} - {default_max:,} ¥/㎡")

                    use_custom = input(f"  是否自定义{zone}区单价? [y/N]: ").strip().lower()

                    if use_custom == 'y':
                        min_price_input = input(f"    最低单价 (¥/㎡) [default: {default_min:,}]: ").strip()
                        max_price_input = input(f"    最高单价 (¥/㎡) [default: {default_max:,}]: ").strip()

                        min_price = int(min_price_input) if min_price_input else default_min
                        max_price = int(max_price_input) if max_price_input else default_max

                        if min_price >= max_price:
                            print("  ⚠️ 最低价不能大于等于最高价，使用默认值")
                            min_price, max_price = default_min, default_max

                        zone_price_config[zone] = {'min': min_price, 'max': max_price}
                        print(f"  ✅ {zone}区单价设置为: {min_price:,} - {max_price:,} ¥/㎡\n")
                    else:
                        print("  ✅ 使用默认单价\n")

                    # ==========================================
                    # 🆕 7.1 CLI: Rental Price Configuration
                    # ==========================================
                    default_rent = {
                        'A': temp_config.get('market.rental.zone_a_rent_per_sqm', 100),
                        'B': temp_config.get('market.rental.zone_b_rent_per_sqm', 60)
                    }

                    print(f"  🏘️ {zone}区 租金水平配置 (元/㎡/月)")
                    rent_input = input(f"    平均租金 [default: {default_rent[zone]}]: ").strip()
                    rent_val = float(rent_input) if rent_input else default_rent[zone]

                    # Store in config structure
                    # We need to structure this to push to config later
                    if 'rental_config' not in locals():
                        rental_config = {}
                    rental_config[zone] = rent_val
                    print(f"  ✅ {zone}区 租金设置为: {rent_val} 元/㎡/月\n")

                # 暂存配置，稍后应用到 config 对象
                if zone_price_config:
                    print("✅ 区域单价配置已暂存")
                if 'rental_config' in locals() and rental_config:
                    print("✅ 租金配置已暂存\n")

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
                    continue  # Loop back

                if warnings:
                    print("\n⚠️  配置警告:")
                    for warn in warnings:
                        print(f"  {warn}")
                    print("\n这些配置可能导致交易不活跃，但可以继续运行。")
                    confirm = input("\n是否继续? [Y/n]: ").strip().lower()
                    if confirm == 'n':
                        print("已取消模拟。")
                        continue  # Loop back
                else:
                    print("\n✅ 配置检查通过！")

                # === 最终确认 ===
                print("\n" + "=" * 60)
                print("【步骤 4/4】配置总览与确认")
                print("=" * 60)

                months = int(input_default("\n模拟月数", "12"))

                print("\n配置总览:")
                print(f"  - Agent总数: {agent_count}")
                for tier_key, tier_data in agent_config.items():
                    tier_names = {'ultra_high': '超高', 'high': '高', 'middle': '中', 'low_mid': '中低', 'low': '低'}
                    print(f"      {tier_names[tier_key]}收入: {tier_data['count']}人, "
                          f"收入{tier_data['income_range'][0] // 1000}-{tier_data['income_range'][1] // 1000}k, "
                          f"拥房{tier_data['property_count'][0]}-{tier_data['property_count'][1]}套")
                print(f"  - 房产总数: {property_count}")
                print(f"  - 模拟月数: {months}")
                print(f"  - 随机种子: {seed_to_use or '随机'}")

                confirm = input("\n确认启动模拟? [Y/n]: ").strip().lower()
                if confirm == 'n':
                    print("已取消模拟。")
                    continue  # Loop back

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

                # [Fix] Apply deferred zone price configuration
                if 'zone_price_config' in locals() and zone_price_config:
                    for zone, prices in zone_price_config.items():
                        config.update(f'market.zones.{zone}.price_per_sqm_range.min', prices['min'])
                        config.update(f'market.zones.{zone}.price_per_sqm_range.max', prices['max'])

                # 🆕 7.1 Apply deferred rental configuration
                if 'rental_config' in locals() and rental_config:
                    config.update('market.rental.zone_a_rent_per_sqm', rental_config.get('A', 100))
                    config.update('market.rental.zone_b_rent_per_sqm', rental_config.get('B', 60))

                # config.save() # ❌ Disabled to preserve Chinese comments in baseline.yaml copy

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
            # NEW: Researcher Intervention Panel
            show_intervention_menu(runner)

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

            # === 5. Auto Forensic Check ===
            print("\n" + "=" * 50)
            check_now = input("是否立即运行逻辑体检 (Forensic Analysis)? [y/N]: ").strip().lower()
            if check_now == 'y':
                import subprocess
                print("🚀 Launching Forensic Analysis...")
                subprocess.run([sys.executable, "generate_enhanced_diaries.py", "--db", db_path, "--mode", "batch"])

        except KeyboardInterrupt:
            print("\n🛑 Simulation Stopped by User.")
        except Exception as e:
            print(f"\n❌ FATAL ERROR: {e}")
            import traceback
            traceback.print_exc()

        print("\nPress Enter to return to main menu...")
        input()


if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()
