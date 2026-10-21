# Adventure asset library expansion — 2026-10-21

Implemented in the existing adventure pipeline and Phaser adapter. Ninja Adventure is the default artwork for new adventures. Tiny RPG Forest is an independent forest theme selected by an Ansimuz/Tiny RPG prompt or the Amber Grove sample. Existing platformer assets and the legacy Kenney adventure rendering path remain available.

## Acquisition and license verification

Downloaded the freely offered archives directly from the creators' itch.io pages. Verified their actual archive contents and included license documents, rather than relying only on listing labels:

| Pack | Official source | Download inspected | License evidence |
| --- | --- | --- | --- |
| Ninja Adventure | https://pixel-boy.itch.io/ninja-adventure-asset-pack | 94,022,790 bytes; 2,674 ZIP entries including directories | Included `LICENSE.txt` (CC0 1.0 Universal) and `README.md`; created by Pixel-Boy and AAA |
| Tiny RPG Forest | https://ansimuz.itch.io/tiny-rpg-forest | 8,151,132 bytes; 632 ZIP entries including Mac metadata | Included two-page `public-license.pdf`; names Luis Zuno / Ansimuz and explicitly permits use, modification and redistribution under CC0 |

The Tiny RPG dungeon download is paid and was not downloaded or integrated. No CraftPix resources, accounts, payments, training or validation inputs were used. Downloaded demo/Godot source was inspected only as data where relevant and was not executed or copied into the runtime. Raw archives and unused resources remain in the ignored `aether-backend/artifacts/asset-imports` directory.

Archive SHA-256 values are recorded in `docs/evidence/asset-expansion/acquisition.json` and pinned in the import script. Public resources include the original Ninja license/README and Tiny license PDF. The PDF was text-extracted and visually rendered for license review; its first page is retained as evidence. No signed download URLs or session tokens are exported.

## Catalog and runtime integration

`aether-frontend/public/assets/adventure/catalog.json` contains 52 curated resources totaling approximately 1 MB, grouped into environment, character, NPC, enemy, decoration, interactive object, collectible, UI and VFX categories. This is a reviewed subset of the downloaded packs, not a claim that every raw resource has been implemented.

Ninja provides six player candidates, fourteen NPC candidates, twelve monsters, terrain/buildings, herbs, keys, gems, chests, projectile/defeat effects, health UI and tree decoration. Tiny provides its hero, mole and treant enemies, forest terrain, pickups, projectile/death effects and environmental props. Larger bosses, audio/music, crafting resources and other unused material remain outside the runtime catalog; possessing artwork does not enable those mechanics.

Every entry records a stable ID, semantic category/tags, pack/style family, source path, source pack URL through its pack, license/redistribution status, dimensions, frame geometry, checksum, scale, collision-body alignment and explicit authored animation sequences where available. The importer records derived-sheet provenance. Normalization only crops, repacks, mirrors supplied side frames or composites authored cells; it generates no AI artwork. Ninja character/monster sheet layouts and Tiny's separate idle/walk sheets are normalized without importing authored demo maps.

`services/adventure_assets.py` resolves artwork from the validated design, actor names/roles/items, environment, combat requirements, prompt style and seed. Player/NPC/enemy IDs and all resource dependencies are persisted in `AdventureIR.art`. A peaceful game selects no enemy textures. Keys map to key art, herbs to foliage items, NPC healer roles to suitable characters and requested mage/ranger/knight players to matching candidates. Other compatible candidates use deterministic seed selection.

One game uses one visual family. Tiny Forest currently supports forest exploration/collection/combat; it lacks the catalog's NPC, door, switch, treasure and interior roles. A request needing those features selects the complete Ninja family for the whole game and records the reason, rather than dropping gameplay or mixing styles. A registered `kenney_tiny` style or older IR without `art` uses the existing compatibility renderer. New packs can be added through the catalog/import boundary with reviewed licensing and matching terrain/role definitions; model-authored asset URLs are not accepted.

The Phaser adapter loads selected dependencies, builds tilemaps from generated logical maps, applies authored directional idle/walk/attack animations, renders selected NPCs/items/monsters, updates switch/door art and plays an authored defeat effect. Asset-specific frame padding is accounted for when aligning feet and collision bodies. Terrain edge tiles follow the generated paths. Game layout, placement, objectives and progression still come from the seeded world specification; no original demo map is substituted.

The real v2 pipeline adds `SELECTING_ASSETS`, `asset_selection.json` and `asset_export_manifest.json` to Inspector evidence. Build manifests identify the selected pack. Creator attribution and the blueprint reflect the actual visual family. The original two Gemini games were upgraded through `scripts/upgrade_adventure_art.py`: the script asserts that every non-art IR field is unchanged and preserves the prior IR in versioned upgrade artifacts. No new model request or automatic map/quest repair is claimed.

## Redistribution boundary

`redistribution_manifest()` produces an explicit allowlist of selected files and original licenses, with source/checksum metadata. It checks path confinement, current checksums, coherent style and CC0 redistribution eligibility. Restricted/unreviewed licenses or mixed families are rejected by the bundle contract. Raw ZIPs, unused resources and downloaded project code are excluded. This supplies an asset boundary for future game/project export; a full source-export product feature is not added here. Privately licensed replacement packs will need an explicit reviewed licensing/export policy before import.

## Verification

- Catalog integrity: **77/77 checks pass**, covering all 52 images, dimensions, hashes, frame bounds, nonempty terrain roles, animations, license files and semantic role references.
- Targeted backend suite: **38 passed** (asset selection/export safeguards, adventure contracts/worlds, platformer and v2 API lifecycle).
- Frontend behavior/state suite: **17 passed**. TypeScript/Vite production build and ESLint pass; the existing Phaser chunk-size advisory remains.
- Real API jobs: **83/83 browser checks pass** across the four cases below. Checks include actual resource loading, observed changing animation frames and direction, zero-gravity movement, collisions, dialogue, pickups/delivery, optional combat/loss, gates, transitions, completion and restart.
- Actual creator form submission and desktop/mobile UI checks: **12/12 pass**, including Inspector, blueprint, typing isolation, toolbar restart, expansion, touch movement and readable dialogue. The fixture generation made no model call.

| API case | Job ID | Checks | Status |
| --- | --- | --- | --- |
| Saved Gemini village, Ninja upgrade | `a6ed2959-515e-4b56-b601-30a9bce305ae` | 23/23 | READY |
| Saved Gemini dungeon, Ninja upgrade | `1fdc15eb-df61-430f-9cc1-ce0e5c0c4ba4` | 25/25 | READY |
| Fresh Ninja village fixture | `b2a6c428-b532-46ba-89e4-ba2a93b22d35` | 16/16 | READY |
| Fresh Tiny Forest fixture | `5a577c70-61b5-4f56-96c6-dda9c8ea98cc` | 19/19 | READY |

Reports, API exports, screenshots and acquisition/license evidence are under `docs/evidence/asset-expansion`. Browser verification uses disclosed controlled positions and real input/physics; it does not certify autonomous navigation or artistic quality. Screenshots were manually reviewed. Early integration checks exposed a short NPC sheet, empty monster animation sequences, an empty secondary terrain cell, an incorrect VFX slice width and padded-frame pickup alignment. These were corrected; earlier failed reports remain preserved. Tiny's death sheet was checked against its six original 30×32 PNG frames.

No new model calls, provider configuration changes, deployment, unrelated refactor or dependency migration occurred. Existing game/quest capability limits still apply; imported art does not add boss AI, shops, equipment, crafting, water traversal or music behavior.

## Reproduction and extension

The local validation setup remains backend port 8001 (`data/iteration5.db`, `artifacts/iteration5`) and Vite port 5174 with `AETHER_BACKEND_URL=http://127.0.0.1:8001`. Normal 8000/5173 setup is also unchanged; restart the backend to load new Python modules.

```powershell
# From repository root; source archives/extracted directories are local, ignored inputs.
# Asset import tooling uses Pillow; running the generator does not require Pillow.
aether-backend/venv/Scripts/python.exe scripts/build_adventure_catalog.py

# From aether-backend
./venv/Scripts/python.exe -m pytest tests/test_adventure_assets.py tests/test_adventure.py tests/test_platformer.py tests/test_platformer_api.py -q
./venv/Scripts/python.exe -m services.adventure_qa 'http://localhost:5174/studio?example=rpg-forest' ../docs/evidence/asset-expansion/reproduction

# From aether-frontend
npm run build
npm run lint
node --experimental-strip-types --test tests/adventure-state.test.mjs tests/platformer-behaviors.test.mjs
```

The importer expects the extracted official archives at `aether-backend/artifacts/asset-imports/ninja/Ninja Adventure - Asset Pack` and `.../tiny-rpg/tiny-RPG-forest-files`, plus the verified `ninja.zip` and `tiny-rpg.zip` in their parent. A different archive hash requires renewed content/license review before updating the pinned hash. The original public license files are the authoritative copies; the optional extracted PDF text is for inspection only.

Try `/studio?example=village`, `/studio?example=dungeon` or `/studio?example=rpg-forest`. Natural-language generation continues to choose the runtime automatically. The Inspector's selected asset bundle/export manifest distinguishes library availability from resources actually resolved for a game.
