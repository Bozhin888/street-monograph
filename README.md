# Street Monograph

A website for a monograph of street and documentary photography: 103 photographers in nine parts.

- `index.html` - animated title sequence on the history of photography (camera obscura to the sensor)
- `book.html` - the monograph: fact-checked bios, key works, lineage, timelines, and the fact-check log
- `data.js` - all content (generated)
- `commons.js` - loads public-domain photographs from Wikimedia Commons at view time

Static site, no build step. Photographs still in copyright are not reproduced; each has a link to find it.

## Regenerating the data

`build/` holds the pipeline: `parse.py` reads the draft, `corrections.py` lists every fact correction,
`works.py` holds the verified key works, and `build2.py` writes `data.js`.
