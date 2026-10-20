# Platformer artwork

Kenney Pixel Platformer 1.2 and Industrial Expansion, CC0.

- https://kenney.nl/assets/pixel-platformer
- https://kenney.nl/assets/pixel-platformer-industrial-expansion

Original licenses are in `platformer/`. Atlases are packed (no spacing): terrain 360×162, industrial 288×126, characters 216×72. Environment frames are 18×18; character frames are 24×24. Repeating 48×72 backgrounds are crops from the original background atlas. No redundant individual tiles are bundled.

`registry.json` records sources, dimensions, semantic roles, animations and SHA-256 checksums. Update checksums when intentionally replacing art. The backend validates dependencies before building. Two green player frames provide idle/run/jump/fall presentation; damage uses blinking because the pack has no dedicated damage animation.
