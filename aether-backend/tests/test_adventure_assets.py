import copy
import pytest
from pydantic import ValidationError
from services.adventure_assets import catalog,validate_catalog,choose_art,redistribution_manifest
from services.adventure import fixture_design,construct
from schemas.assets import AdventureArt
from tests.test_adventure import VILLAGE,DUNGEON


def test_catalog_dimensions_hashes_animation_frames_and_categories():
    data=catalog();report=validate_catalog(data)
    assert report['overall']=='PASS',[c for c in report['checks'] if not c['passed']]
    assert {'environment','character','npc','enemy','decoration','interactive_object','collectible','ui','vfx'}<=set(data['packs']['ninja_adventure']['categories'])
    for pack in data['packs'].values():assert pack['redistributable'] and pack['license']=='CC0-1.0'


def test_invalid_or_empty_animation_frames_fail_integrity():
    for frames in [[],[999999]]:
        data=copy.deepcopy(catalog());data['assets']['ninja_skull']['animations']['down']['walk']=frames
        assert validate_catalog(data)['overall']=='FAIL'
    data=copy.deepcopy(catalog());path=data['packs']['tiny_rpg_forest']['terrain']['path']
    data['assets']['tiny_terrain']['nonempty_frames'].remove(path)
    assert validate_catalog(data)['overall']=='FAIL'


def test_semantic_selection_is_seeded_coherent_and_combat_optional():
    peaceful=choose_art(fixture_design(VILLAGE),VILLAGE,42)
    dungeon=choose_art(fixture_design(DUNGEON),DUNGEON,42)
    assert peaceful==choose_art(fixture_design(VILLAGE),VILLAGE,42)
    assert peaceful.pack_id==dungeon.pack_id=='ninja_adventure'
    assert not any(a.category=='enemy' for a in peaceful.assets.values())
    assert any(a.category=='enemy' for a in dungeon.assets.values())
    assert peaceful.actors['guide']=='ninja_woman'
    assert peaceful.actors['herbs']=='ninja_herb' and dungeon.actors['relic']=='ninja_key'
    for art in [peaceful,dungeon]:assert {a.style_family for a in art.assets.values()}=={art.style_family}
    assert construct(fixture_design(VILLAGE),VILLAGE,42).areas!=construct(fixture_design(DUNGEON),DUNGEON,42).areas


def test_tiny_forest_theme_and_whole_game_fallback():
    prompt='Ansimuz Tiny RPG top-down forest adventure, explore a grove and fight monsters'
    design=fixture_design(prompt);art=choose_art(design,prompt,2)
    assert art.pack_id=='tiny_rpg_forest' and art.player=='tiny_hero'
    assert all(a.pack_id=='tiny_rpg_forest' for a in art.assets.values())
    design=fixture_design(VILLAGE);design.art_style='tiny_rpg_forest'
    art=choose_art(design,VILLAGE,42)
    assert art.pack_id=='ninja_adventure' and 'lacks' in art.selection_reason
    design.art_style='unregistered'
    with pytest.raises(ValueError):choose_art(design,VILLAGE,42)


def test_export_allowlist_rejects_unreviewed_licenses_and_mixed_styles():
    art=choose_art(fixture_design(VILLAGE),VILLAGE,42)
    manifest=redistribution_manifest(art)
    assert manifest['files'] and all(f['license']=='CC0-1.0' for f in manifest['files'])
    assert not any('.zip' in f['url'] for f in manifest['files'])
    for field,value in [('license','Restricted'),('style_family','another_pack'),('redistributable',False)]:
        data=art.model_dump();next(iter(data['assets'].values()))[field]=value
        with pytest.raises(ValidationError):AdventureArt.model_validate(data)
