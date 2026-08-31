from pathlib import Path
import csv
import hashlib
import subprocess


ROOT = Path(__file__).resolve().parent
BLENDER = Path(r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe")
GENERATOR = ROOT / "bay_daybed_v4_generator.py"
BLEND = ROOT / "bay_daybed_v4.blend"
CUTLIST = ROOT / "bay_daybed_v4_cutlist.csv"
DIMENSIONS = ROOT / "bay_daybed_v4_dimensions.txt"


def run_blender_expr(expr):
    bootstrap = f"import runpy; n=runpy.run_path({str(GENERATOR)!r}); {expr}"
    return subprocess.run(
        [str(BLENDER), "--background", "--python-expr", bootstrap],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


def run_generator():
    return subprocess.run(
        [str(BLENDER), "--background", "--python", str(GENERATOR)],
        cwd=ROOT, capture_output=True, text=True,
    )


def run_saved_expr(expr):
    return subprocess.run(
        [str(BLENDER), str(BLEND), "--background", "--python-expr", expr],
        cwd=ROOT, capture_output=True, text=True,
    )


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    result = run_blender_expr(
        "n['validate_parameters'](); print('V4 PARAMETER VALIDATION PASSED')"
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "V4 PARAMETER VALIDATION PASSED" in output, output

    center_expr = (
        "n['reset_scene'](); n['configure_units'](); "
        "c=n['create_collections'](); m=n['create_materials'](); "
        "center=n['build_center'](c,m); n['validate_center'](center); "
        "assert len(center['upper'])==7; assert len(center['lower'])==6; "
        "assert len(center['posts'])==10; "
        "assert n['union_bounds'](center['upper'])==(-29.5,29.5,0.0,31.5,8.25,9.75); "
        "assert n['union_bounds'](center['lower'])==(-29.5,29.5,0.0,29.0,0.0,1.5); "
        "print('V4 CENTER VALIDATION PASSED')"
    )
    result = run_blender_expr(center_expr)
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "V4 CENTER VALIDATION PASSED" in output, output

    side_expr = (
        "n['reset_scene'](); n['configure_units'](); "
        "c=n['create_collections'](); m=n['create_materials'](); "
        "sides=n['build_sides'](c,m); metrics=n['localized_step_metrics'](sides); "
        "assert abs(metrics['interface']-3.085786437626905)<1e-6; "
        "assert abs(metrics['edge_clearance']-3.181980515339464)<1e-6; "
        "assert metrics['max_spine_overlap']==0.0; n['validate_sides'](sides); "
        "assert len(sides['LEFT']['upper'])==8; assert len(sides['LEFT']['lower'])==7; "
        "assert len(sides['LEFT']['posts'])==8; "
        "assert len(sides['RIGHT']['upper'])==8; assert len(sides['RIGHT']['lower'])==7; "
        "assert len(sides['RIGHT']['posts'])==8; "
        "assert all(o['cut_type']=='SQUARE / 90 DEGREE' for d in sides.values() for o in d['upper']+d['lower']+d['posts']); "
        "assert all(o['status']=='PROVISIONAL / FIELD VERIFY' for d in sides.values() for o in d['upper']+d['lower']+d['posts']); "
        "print('V4 SIDE STRUCTURE VALIDATION PASSED')"
    )
    result = run_blender_expr(side_expr)
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "V4 SIDE STRUCTURE VALIDATION PASSED" in output, output

    fastener_expr = (
        "n['reset_scene'](); n['configure_units'](); "
        "c=n['create_collections'](); m=n['create_materials'](); "
        "center=n['build_center'](c,m); sides=n['build_sides'](c,m); "
        "fasteners=n['build_fastener_references'](sides,c,m); "
        "sequenced=[s for s in fasteners if s.get('assembly_sequence_required',False)]; "
        "assert len(sequenced)==4; assert all(s['end']=='FRONT' and 'LOWER_OUTER_STEP_02' in s['target_purpose'] for s in sequenced); "
        "n['validate_fasteners'](sides,fasteners); spans=n['calculate_support_spans'](center,sides); "
        "assert len(fasteners)==28; assert spans['LEFT']<16; assert spans['RIGHT']<16; "
        "assert all(p['post_screw_access'] for d in sides.values() for p in d['posts']); "
        "print('V4 FASTENER AND SUPPORT VALIDATION PASSED')"
    )
    result = run_blender_expr(fastener_expr)
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "V4 FASTENER AND SUPPORT VALIDATION PASSED" in output, output

    visual_expr = (
        "n['reset_scene'](); n['configure_units'](); "
        "c=n['create_collections'](); m=n['create_materials'](); "
        "center=n['build_center'](c,m); sides=n['build_sides'](c,m); "
        "visuals=n['build_visuals'](c,m,center,sides); n['validate_visuals'](visuals,sides); "
        "assert m['reference'].diffuse_color[3]==1.0; "
        "assert len(visuals['decks'])==3; assert len(c['CUSHION_REFERENCE'].objects)==1; "
        "assert n['bpy'].context.scene.render.engine=='BLENDER_WORKBENCH'; "
        "assert visuals['layers']['FRAMING_ONLY'].layer_collection.children['ROOM_REFERENCE'].exclude; "
        "assert 'TOP_FRAMING' in visuals['layers']; "
        "assert visuals['cameras']['V4_TOP_FRAMING']['recommended_view_layer']=='TOP_FRAMING'; "
        "assert n['bounds'](visuals['decks']['LEFT'])[0]>=30-1e-6; "
        "assert n['bounds'](visuals['decks']['RIGHT'])[1]<=-30+1e-6; "
        "assert n['positive_overlap_area'](n['object_footprint'](visuals['cushion']),n['object_footprint'](visuals['decks']['LEFT']))<1e-6; "
        "assert n['positive_overlap_area'](n['object_footprint'](visuals['cushion']),n['object_footprint'](visuals['decks']['RIGHT']))>1.0; "
        "assert all(cam.scale.x>0 for cam in visuals['cameras'].values()); "
        "assert visuals['cameras']['V4_FRONT'].data.ortho_scale>=85; "
        "assert all(o.hide_render for o in visuals['dimensions'] if o.type=='FONT'); "
        "assert len([o for o in visuals['dimensions'] if o.get('nonstructural_deck_footprint_reference',False)])==3; "
        "assert set(visuals['cameras'])=={'V4_TOP_FRAMING','V4_FRAMING_ISOMETRIC','V4_FINISHED_ISOMETRIC','V4_FRONT','V4_RIGHT_DETAIL','V4_LEFT_DETAIL'}; "
        "assert visuals['decks']['LEFT']['status']=='FIELD VERIFY — TEMPLATE TO ACTUAL ROOM BEFORE CUTTING'; "
        "print('V4 FINISH AND ROOM VALIDATION PASSED')"
    )
    result = run_blender_expr(visual_expr)
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "V4 FINISH AND ROOM VALIDATION PASSED" in output, output

    result = run_generator()
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "V4 VALIDATION PASSED" in output, output
    assert all(path.exists() and path.stat().st_size > 0 for path in (GENERATOR, BLEND, CUTLIST, DIMENSIONS))

    with CUTLIST.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        assert reader.fieldnames == ["MODULE", "OBJECT", "QUANTITY", "CUT_LENGTH", "CUT_TYPE", "ORIENTATION", "STATUS"]
    center_counts = {}
    for row in (row for row in rows if row["MODULE"] == "CENTER"):
        length = float(row["CUT_LENGTH"])
        center_counts[length] = center_counts.get(length, 0) + int(row["QUANTITY"])
    assert center_counts == {59.0: 4, 24.5: 5, 22.0: 4, 6.75: 10}
    side_rows = [row for row in rows if row["MODULE"] in {"LEFT", "RIGHT"}]
    assert len(side_rows) == 46
    assert all(row["CUT_TYPE"] == "SQUARE / 90 DEGREE" for row in side_rows)
    assert all(row["STATUS"] == "PROVISIONAL / FIELD VERIFY" for row in side_rows)

    report = DIMENSIONS.read_text(encoding="utf-8")
    assert "VIEWER LEFT — RAISED WOOD LANDING — NO CUSHION" in report
    assert "VIEWER RIGHT — LOWER MODULE — CONTINUOUS CUSHION" in report
    assert "FIELD VERIFY — TEMPLATE TO ACTUAL ROOM BEFORE CUTTING" in report
    assert "ASSEMBLY_SEQUENCE_REQUIRED" in report

    saved_expr = (
        "import bpy; "
        "assert len(bpy.data.collections['LEFT_UPPER_STEP_FRAME'].objects)==8; "
        "assert len(bpy.data.collections['LEFT_LOWER_STEP_FRAME'].objects)==7; "
        "assert len(bpy.data.collections['LEFT_POSTS'].objects)==8; "
        "assert len(bpy.data.collections['RIGHT_UPPER_STEP_FRAME'].objects)==8; "
        "assert len(bpy.data.collections['RIGHT_LOWER_STEP_FRAME'].objects)==7; "
        "assert len(bpy.data.collections['RIGHT_POSTS'].objects)==8; "
        "assert len(bpy.data.collections['CUSHION_REFERENCE'].objects)==1; "
        "assert len([o for o in bpy.data.collections['FASTENER_REFERENCE'].objects if o.get('assembly_sequence_required',False)])==4; "
        "assert bpy.context.scene['viewer_left_module'].startswith('LEFT / POSITIVE X'); "
        "assert bpy.context.scene['viewer_right_module'].startswith('RIGHT / NEGATIVE X'); "
        "assert all(cam.scale.x>0 for cam in bpy.data.collections['CAMERAS'].objects); "
        "assert {'FRAMING_ONLY','FINISHED'} <= {v.name for v in bpy.context.scene.view_layers}; "
        "print('V4 SAVED MODEL AUDIT PASSED')"
    )
    result = run_saved_expr(saved_expr)
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "V4 SAVED MODEL AUDIT PASSED" in output, output

    output_hashes = {path: sha256(path) for path in (BLEND, CUTLIST, DIMENSIONS)}
    corruption_cases = [
        "n['validate_parameters'].__globals__['STRUCTURAL_SIDE_ANGLE']=45.5; n['validate_parameters']()",
        "n['validate_parameters'].__globals__['SIDE_LOWER_FRONT_EDGE_Y']=29.5; n['validate_parameters']()",
        (
            "n['reset_scene'](); c=n['create_collections'](); m=n['create_materials'](); "
            "s=n['build_sides'](c,m); s['LEFT']['upper'][0]['status']='RESOLVED'; n['validate_sides'](s)"
        ),
        (
            "n['reset_scene'](); c=n['create_collections'](); m=n['create_materials'](); "
            "s=n['build_sides'](c,m); f=n['build_fastener_references'](s,c,m); "
            "next(o for o in s['LEFT']['upper'] if 'OUTER_STEP_02' in o['purpose'])['cut_length']=2.0; "
            "n['validate_fasteners'](s,f)"
        ),
        (
            "n['reset_scene'](); c=n['create_collections'](); m=n['create_materials'](); "
            "center=n['build_center'](c,m); s=n['build_sides'](c,m); v=n['build_visuals'](c,m,center,s); "
            "dup=v['cushion'].copy(); dup.data=v['cushion'].data.copy(); c['CUSHION_REFERENCE'].objects.link(dup); "
            "n['validate_visuals'](v,s)"
        ),
    ]
    for index, case in enumerate(corruption_cases, 1):
        result = run_blender_expr(case)
        output = result.stdout + result.stderr
        assert "AssertionError" in output, f"corruption case {index} unexpectedly passed\n{output}"
    assert output_hashes == {path: sha256(path) for path in output_hashes}
    print("V4 FAIL-CLOSED CORRUPTION AUDIT PASSED")


if __name__ == "__main__":
    main()
