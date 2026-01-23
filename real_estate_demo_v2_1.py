#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Oasis Real Estate Simulation Runner (v2.1 Scholar Edition)
Supports: Interactive Menu, Persistence (Resume), Configurable Parameters, seed control.
"""
import sys
import logging
import random
import numpy as np
import time
from simulation_runner import SimulationRunner

# Configure Logging to Console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8' # Force UTF-8
)

def input_default(prompt, default_value):
    """Helper for input with default value"""
    val = input(f"{prompt} [default: {default_value}]: ").strip()
    return val if val else default_value

def main():
    # Force UTF-8 for Windows Console
    try:
        if sys.stdout.encoding != 'utf-8':
            sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

    print("\n" + "=" * 60)
    print("🏠 Oasis Real Estate Sandbox (Scholar Edition v2.2)".center(60))
    print("=" * 60)
    
    # --- 1. Seed Control ---
    seed_val = input_default("Enter Random Seed (for reproducibility)", "random")
    if seed_val != "random":
        try:
            seed_int = int(seed_val)
            random.seed(seed_int)
            np.random.seed(seed_int)
            print(f"✅ Random Seed set to: {seed_int}")
        except ValueError:
            print("⚠️ Invalid seed, using random.")
    
    # --- 2. Mode Selection ---
    print("\nSelect Mode:")
    print("1. Start NEW Simulation (Wipe previous data)")
    print("2. RESUME Simulation (Load from DB)")
    mode = input_default("Choose option", "1")
    
    resume = False
    
    if mode == "2":
        resume = True
        print("📂 Will attempt to resume from 'real_estate_stage2.db'...")
        # Optional: Ask for how many MORE months to run
        months = int(input_default("How many months to simulate?", "12"))
        
        # We need default config for resume, or maybe store config in DB?
        # For now use default
        config = {
            'volatility': 0.03,
            'shock_prob': 0.10,
            'shock_mag': 0.12
        }
    else:
        print("\n--- Configuration ---")
        use_custom = input_default("Use Custom Parameters? (y/N)", "n")
        
        if use_custom.lower() == 'y':
            agent_count = int(input_default("Agent Count", "100"))
            months = int(input_default("Months to Simulate", "12"))
            shock_prob = float(input_default("Market Shock Probability (0.0-1.0)", "0.10"))
            shock_mag = float(input_default("Shock Magnitude (0.0-0.5)", "0.12"))
            volatility = float(input_default("Normal Volatility (e.g. 0.03)", "0.03"))
        else:
            agent_count = 100
            months = 12
            shock_prob = 0.10
            shock_mag = 0.12
            volatility = 0.03
            print("✅ Using Default Parameters.")
            
        config = {
            'volatility': volatility,
            'shock_prob': shock_prob,
            'shock_mag': shock_mag
        }
    
    # --- 3. Execution ---
    print("\n🚀 Initializing Runner...")
    
    # Note: If resuming, agent_count is ignored (loaded from DB)
    runner = SimulationRunner(
        agent_count=agent_count if not resume else 0,
        months=months,
        resume=resume,
        config=config
    )
    
    try:
        runner.run()
        print("\n✅ Simulation Completed Successfully.")
        
        # --- 4. Auto Export ---
        print("\n📦 Exporting Results...")
        try:
            import scripts.export_results as exporter
            exporter.export_data()
        except ImportError:
            # Fallback if module logic isn't perfect importable, run via command
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
