from collections import Counter
from pathlib import Path
import csv
import subprocess


ROOT = Path(__file__).resolve().parent
BLENDER = Path(r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe")


def main():
    result = subprocess.run(
        [str(BLENDER), "--background", "--python", str(ROOT / "center_daybed_module_v2_generator.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "V2 VALIDATION PASSED" in output, output
    for name in (
        "center_daybed_module_v2.blend",
        "center_daybed_module_v2_cutlist.csv",
        "center_daybed_module_v2_dimensions.txt",
    ):
        assert (ROOT / name).is_file(), name
    with (ROOT / "center_daybed_module_v2_cutlist.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    totals = Counter()
    for row in rows:
        totals[float(row["cut_length_in"])] += int(row["quantity"])
    assert totals == Counter({59.0: 4, 24.5: 5, 22.0: 4, 6.75: 10})
    report = (ROOT / "center_daybed_module_v2_dimensions.txt").read_text(encoding="utf-8")
    assert "Front-panel nailers remain above and independent of the recessed lower frame: PASS" in report
    assert "Front-post upper bearing: 2.500 in under member; 1.000 in under front rail: PASS" in report
    assert "Primary top fastening for front posts passes through the upper front-to-back member" in report

    inspection_code = r'''
import bpy

def bounds(obj):
    x, y, z = obj.location
    dx, dy, dz = obj.dimensions
    return (x-dx/2, x+dx/2, y-dy/2, y+dy/2, z-dz/2, z+dz/2)

posts = list(bpy.data.collections["VERTICAL_POSTS"].objects)
front = [obj for obj in posts if obj["post_row"] == "FRONT"]
upper = list(bpy.data.collections["UPPER_FRAME_FLAT_2X4"].objects)
lower = list(bpy.data.collections["LOWER_FRAME_FLAT_2X4"].objects)
members = [obj for obj in upper if obj["validation_group"] in {"upper_outside", "upper_interior"}]
upper_front = next(obj for obj in upper if obj["purpose"] == "UPPER_FRONT_RAIL")
lower_front = next(obj for obj in lower if obj["purpose"] == "LOWER_FRONT_RAIL")
assert len(front) == 5
for post in front:
    post_box = bounds(post)
    member = next(obj for obj in members if abs(obj.location.x - post.location.x) < 1e-6)
    member_box, upper_front_box, lower_front_box = bounds(member), bounds(upper_front), bounds(lower_front)
    assert tuple(round(value, 3) for value in post.dimensions) == (1.5, 3.5, 6.75)
    assert round(post.location.y, 3) == 27.25
    assert tuple(round(value, 3) for value in post_box[2:4]) == (25.5, 29.0)
    assert lower_front_box[0] <= post_box[0] and lower_front_box[1] >= post_box[1]
    assert tuple(round(value, 3) for value in lower_front_box[2:4]) == tuple(round(value, 3) for value in post_box[2:4])
    assert member_box[0] <= post_box[0] and member_box[1] >= post_box[1]
    assert round(min(post_box[3], member_box[3]) - max(post_box[2], member_box[2]), 3) == 2.5
    assert round(min(post_box[3], upper_front_box[3]) - max(post_box[2], upper_front_box[2]), 3) == 1.0
print("FRONT POST SPLIT-BEARING AUDIT PASSED")
'''
    inspection = subprocess.run(
        [str(BLENDER), "--background", str(ROOT / "center_daybed_module_v2.blend"), "--python-expr", inspection_code],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    inspection_output = inspection.stdout + inspection.stderr
    assert inspection.returncode == 0, inspection_output
    assert "FRONT POST SPLIT-BEARING AUDIT PASSED" in inspection_output


if __name__ == "__main__":
    main()
