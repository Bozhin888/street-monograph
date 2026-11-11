/* Loads public-domain photographs from Wikimedia Commons at view time.
   Only works marked with a Commons search (w.c) are ever requested, and Commons hosts free files only. */
(function () {
  const mem = new Map();
  const KEY = "sm-commons-v1:";
  function cached(q) {
    if (mem.has(q)) return mem.get(q);
    try { const v = sessionStorage.getItem(KEY + q); if (v) { const o = JSON.parse(v); mem.set(q, Promise.resolve(o)); return mem.get(q); } } catch (e) {}
    return null;
  }
  function find(q, width) {
    const hit = cached(q);
    if (hit) return hit;
    const url = "https://commons.wikimedia.org/w/api.php?action=query&format=json&origin=*&generator=search&gsrnamespace=6&gsrlimit=1" +
      "&gsrsearch=" + encodeURIComponent(q + " filetype:bitmap") + "&prop=imageinfo&iiprop=url&iiurlwidth=" + (width || 960);
    const p = fetch(url).then(r => r.ok ? r.json() : null).then(j => {
      const pages = j && j.query && j.query.pages; if (!pages) return null;
      const pg = Object.values(pages)[0]; const ii = pg && pg.imageinfo && pg.imageinfo[0]; if (!ii) return null;
      const o = { src: ii.thumburl || ii.url, page: ii.descriptionurl, file: (pg.title || "").replace(/^File:/, "").replace(/\.[a-z]+$/i, "") };
      try { sessionStorage.setItem(KEY + q, JSON.stringify(o)); } catch (e) {}
      return o;
    }).catch(() => null);
    mem.set(q, p);
    return p;
  }
  window.SMCommons = { find };
})();
