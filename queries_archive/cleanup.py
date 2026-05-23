"""Clean up debug/test scripts from BHBeacon queries dir"""
import os, glob

root = os.path.dirname(os.path.abspath(__file__))
# Clean all _test_*, _debug_*, _check_*, _simbad_*.py files
patterns = ["_test_*.py", "_debug_*.py", "_check_*.py", "_simbad_*.py", "_show_*.py", "_check_astro.py"]
for p in patterns:
    for f in glob.glob(os.path.join(root, p)):
        os.remove(f)
        print("Removed:", os.path.basename(f))
        
print("Done. Kept main scripts.")
