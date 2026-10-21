# Adventure artwork

New adventures use the reviewed `catalog.json` and `library/` resources: Ninja Adventure (Pixel-Boy/AAA) is primary; Tiny RPG Forest (Ansimuz) is a separate forest-only family. Both included archive licenses were verified as CC0, and original license documents ship alongside the curated resources. The catalog records semantic roles, authored animation sequences, pixel/frame dimensions, provenance and checksums. The backend selects one coherent family from the validated specification and persists the resolved bundle in GameIR.

See `docs/ASSET_LIBRARY_EXPANSION.md` and `scripts/build_adventure_catalog.py` for acquisition, redistribution safeguards, selection rules, extension and verification. Imported resources total 52 curated assets; unused full-pack content and raw archives are not public/export dependencies.

## Kenney compatibility artwork

Kenney's Tiny Town and Tiny Dungeon, licensed CC0-1.0. Original license files are included beside each atlas.

- https://kenney.nl/assets/tiny-town
- https://kenney.nl/assets/tiny-dungeon
- https://creativecommons.org/publicdomain/zero/1.0/

Both packed atlases use 16×16 frames, 12 columns, 192×176 pixels. The runtime scales these to a 32-pixel world grid. Registry metadata records URLs, roles, source, license, dimensions and SHA-256 checksums. Validation checks both dimensions and checksums before assembly. Changing artwork requires updating the registry and the adapter's frame mappings to match the replacement atlas.

These packs contain single-frame characters. The runtime animates movement with directional horizontal mirroring, stride tilt and bob; it does not claim authored four/eight-direction animation frames. Contact sheets used to inspect frame roles are saved in docs/evidence/iteration5.
