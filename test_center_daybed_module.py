from pathlib import Path
import csv
import subprocess


ROOT = Path(__file__).resolve().parent
BLENDER = Path(r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe")


def main():
    result = subprocess.run(
        [str(BLENDER), "--background", "--python", str(ROOT / "center_daybed_module_generator.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "VALIDATION PASSED" in output, output
    assert "- Vertical risers: 10" in output, output
    assert (ROOT / "center_daybed_module.blend").is_file()
    cutlist = ROOT / "center_daybed_2x4_cutlist.csv"
    assert cutlist.is_file()
    with cutlist.open(newline="", encoding="utf-8") as handle:
        rows = {row["purpose"]: row for row in csv.DictReader(handle)}
    assert rows["VERTICAL_RISER"]["quantity"] == "10", rows["VERTICAL_RISER"]


if __name__ == "__main__":
    main()
