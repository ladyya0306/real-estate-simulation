
import sys
import os
import shutil

sys.path.append(os.getcwd())

from generate_simulation_report import generate_wealth_distribution, ensure_dir

def verify_chart():
    print("Verifying P2 (Wealth Chart)...")
    
    test_dir = "results/test_chart"
    ensure_dir(test_dir)
    
    try:
        generate_wealth_distribution(test_dir)
        
        file_path = f"{test_dir}/wealth_distribution.png"
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            print(f"✅ Chart generated: {file_path} ({size/1024:.1f} KB)")
            if size > 1000:
                print("✅ Chart file size seems reasonable")
            else:
                print("⚠️ Chart file seems too small")
        else:
            print("❌ Chart file not found")
            
    except Exception as e:
        print(f"❌ Error generating chart: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_chart()
