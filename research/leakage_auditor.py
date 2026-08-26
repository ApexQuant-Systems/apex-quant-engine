import os
import re

def perform_leakage_audit():
    sacred_files = [
        "v3_architecture/hierarchical_decision_engine.py",
        "v3_architecture/forward_testing_engine.py",
        "v3_architecture/multi_horizon_tournament.py"
    ]
    
    # Common code patterns where look-ahead data leaks hide
    leakage_vectors = {
        "Negative Index Shift Overlook": r"shift\((?!-[1-9]|\d)\)", 
        "Future Row Reference": r"iloc\[i\s*\+\s*[1-9]",
        "Unshifted Resample Join": r"\.join\(.*resample",
        "Lookahead Rolling Calculation": r"\.rolling\(.*min_periods=1"
    }
    
    print("=====================================================================")
    
    for file_path in sacred_files:
        if not os.path.exists(file_path):
            continue
            
        print(f"🔬 Auditing Core Logic for Leakage: {file_path}")
        with open(file_path, "r") as f:
            lines = f.readlines()
            
        file_clean = True
        for name, pattern in leakage_vectors.items():
            for idx, line in enumerate(lines):
                if re.search(pattern, line) and not line.strip().startswith("#"):
                    print(f"  ├── ⚠️ {name} POTENTIAL RISK at Line {idx + 1}:")
                    print(f"  │   └── Code: {line.strip()}")
                    file_clean = False
                    
        if file_clean:
            print("  └── 🟢 No obvious structural look-ahead syntax detected.")
            
    print("=====================================================================")

if __name__ == "__main__":
    perform_leakage_audit()
