"""Smoke test for the local code sandbox.

Run after building the image:
    docker build -t mentis-sandbox:latest backend/sandbox
    py -3.12 backend/sandbox/smoke_test.py

Exercises the full essentials stack (numpy/pandas/scipy/sympy/matplotlib) plus
CoolProp thermophysical properties, and verifies a PNG is produced in the
mounted workspace.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))  # backend/
from app.sandbox import run_python  # noqa: E402

WORKSPACE = pathlib.Path(__file__).resolve().parents[1] / ".data" / "sandbox-smoke"

CELL = r"""
import numpy, pandas as pd, scipy, sympy, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import CoolProp.CoolProp as CP

print("numpy", numpy.__version__, "| pandas", pd.__version__, "| scipy", scipy.__version__)

# Thermophysics: saturated water near a typical generator temperature (80 C).
T = 353.15
psat = CP.PropsSI("P", "T", T, "Q", 0, "Water") / 1000.0
hf = CP.PropsSI("H", "T", T, "Q", 0, "Water") / 1000.0
print(f"water @80C: Psat={psat:.1f} kPa, hf={hf:.1f} kJ/kg")

# Dataframe + figure -> /workspace
df = pd.DataFrame({"T_gen_C": [40, 60, 80, 100], "COP": [0.55, 0.62, 0.71, 0.74]})
print(df.to_string(index=False))

fig, ax = plt.subplots(figsize=(4, 3))
ax.plot(df["T_gen_C"], df["COP"], marker="o", color="#2f6a4c")
ax.set_xlabel("Generator temperature (°C)")
ax.set_ylabel("COP")
ax.set_title("Single-effect absorption COP")
fig.tight_layout()
fig.savefig("cop_curve.png", dpi=120)
print("wrote cop_curve.png")
"""

if __name__ == "__main__":
    res = run_python(CELL, WORKSPACE, timeout=180)
    print("=== exit_code:", res.exit_code, "| timed_out:", res.timed_out, "| ok:", res.ok)
    print("=== files produced:", res.files)
    print("=== STDOUT ===\n" + res.stdout)
    if res.stderr.strip():
        print("=== STDERR ===\n" + res.stderr[:3000])
    sys.exit(0 if res.ok and "cop_curve.png" in res.files else 1)
