# PROGRESS — punkshows app

## Goal
App to find and list all punk + metal shows in the Tacoma–Seattle–Olympia area.
Add-ons: per-band Bandcamp/webpage listen links; final deliverable "android app, dark and basic"
→ delivered as dark installable PWA + offline static snapshot AND a real signed `punkshows.apk`
   (built 2026-10-09 with the toolchain in tools/ + sdk/; see the Android APK section).

## Done (all verified working)
- [x] Sources researched; 3 working: seattleareapunkshows.org (punk flyer wall),
      metalgigs.us (metal, JSON-LD), nocleansinging.com (PNW metal calendar).
      Dead ends: everout.com 403, eventbrite (API key), bandsintown (JS).
- [x] `sources.py` — 3 scrapers → normalized events {date, venue, city, bands, source, genre};
      VENUE_CITY map + OUT_OF_AREA filter. ~330 raw events, 270 in-area shows.
- [x] `cli.py` — CLI listing (--days/--genre/--city/--listen/--json).
- [x] `webapp.py` — Flask dark PWA (manifest+icon, 10-min TTL cache) at :7888.
- [x] `snapshot.py` — self-contained dark `shows.html` (offline, 270 shows).
- [x] `bandcamp.py` — band→listen-URL lookup + `bands_cache.json`.

## Bandcamp lookup — decisions
- DDG lite: permanently bot-blocked here (HTTP 202 anomaly page). Bing/searx/startpage
  all bot-walled too. Bandcamp search API: Client Challenge. ALL dead ends.
- WORKING: MusicBrainz API (bot-friendly, UA required): artist search → url-rels
  → `bandcamp` relation, fallback `official homepage`. ~2.4 s/band (1.2 s sleep, 1 req/s rule).
- `search_bandcamp` = MusicBrainz only now (DDG fallback removed: always blocked, cost 2.5 min/band).
- Cache fill running in background (PID 570, log /tmp/opencode/fill.log): 401 missing bands,
  ~17 min. `bandcamp.py [cap] [clear]` — `clear` drops null entries for retry.

## SAP blank listings fix (2026-10-09)
- Symptom: user saw seattleareapunkshows.org entries with no band names. Root cause: SAP is a
  flyer wall — 121/163 flyers encode only "at <Venue>" in the filename; bands are baked into the
  flyer IMAGE. OCR attempt failed (tesseract + downloaded eng.traineddata → garbage on stylized
  flyers). Dead end.
- Fix: parse_sap now adds `flyer` = absolute image URL; junk filenames (sb/sp) dropped, dupes
  deduped (154 events from 163 imgs). cli.py prints "— see flyer: URL"; webapp/snapshot show
  "🖹 flyer" link (121 in shows.html, verified 200 image/jpeg). VENUE_CITY extended with SAP venues.
- shows.html now 267 shows (window widened by snapshot defaults); webapp restarted on :8000
  (old instance had died; started fresh, serving 121 flyer links).

## Venue official websites (2026-10-09)
- Ask: which venues have NO official website (app falls back to a Google Maps search link
  in `venue_link()`, sources.py:339 — only "the crypt" had a real site). Deliverable =
  `missingvenues.txt` (written, 30 lines: 17 no-site venues + 1 low-confidence + 5 junk strings).
- Method: 110 unique raw venue strings from `filter_area(all_events())`; alias groups normalized
  by hand (Showbox*/Vera*/Moore*/Neptune*/Clock-Out/Funhouse...). Junk venue strings found and
  excluded: sb, sp, QFC (grocery-store joke flyer), "in tacoma", "guests".
- ~55 venues resolved to official sites (28 by guess+requests-verify, rest by web_search);
  key ones: Moore/Paramount/Neptune -> stgpresents.org, Showbox* -> showboxpresents.com,
  black lodge -> theveraproject.org/blacklodge/, fox theater -> foxtheaterspokane.org (Spokane,
  confirmed by Alter Bridge/Big Wreck event), the yard -> theyardcafe.com, two fingers social ->
  2fingerssocial.com, salem grand theatre -> grandtheatre.com, tacoma dome -> tacomadome.org.
- Search engines from Python are ALL dead (Bing/Mojeek/Marginalia/searx/DDG-lite = captcha or
  zero hrefs). Only the MCP web_search tool works, and DDG bot-blocks it intermittently —
  retry with simpler phrasing a few messages later.
- Both leftovers now resolved as NO-SITE: "Capitol Backstage" = a room inside Capitol Theater
  Olympia (concertarchives.org/venues/capitol-theater-backstage, parent site capitoltheatre.com);
  "Gravel Pit" = Tacoma DIY house, Instagram @gravelpittacoma only (thegravelpit.org is a parked
  GoDaddy page). missingvenues.txt now lists 18 no-site venues + 5 junk strings.
- [x] WIRED (2026-10-09): `venue_link()` (sources.py) now uses VENUE_SITE (~60 canonical→URL
  entries) + VENUE_ALIAS (~30 raw→canonical) + NOT_A_VENUE{sb,sp,qfc,"in tacoma",guests}.
  Coverage over the 111 raw venue strings: 90 official sites, 18 Maps fallback (exactly the
  no-site list), 3 empty. Gotcha fixed: two alias keys had a CYRILLIC 'о' from copy-paste.

## Flyer centering (2026-10-09)
- [x] webapp.py: flyer is now a block `<div class="flyer"><a href=…>{thumb|🖹 flyer}</a></div>`
  after the show text (was inline `<a class="listen">` glued to the end of the line).
  CSS: `.flyer{display:block;margin:.6em auto .2em;text-align:center}`,
  `.thumb{display:block;width:110px;margin:auto;…}` → thumb centers under the text.
- [x] Re-ran snapshot.py → shows.html 274 shows, 154 `<div class="flyer">` blocks, 154 base64
  thumbs inlined, 0 leftover `/thumbs/` refs.

## Android APK — BUILT (2026-10-09)
Artifact: `punkshows.apk` at repo root, 29,005 bytes, signed. Contents:
AndroidManifest.xml (1,104-byte binary) + classes.dex (147,296 B) + META-INF signature.
No clang/AOSP download was ever needed — `d8` (in cmdline-tools AND build-tools) is the DEX
assembler, so it replaced the AOSP clang + aic + `so` pipeline entirely.

Setup (all local): `sdkmanager --sdk_root=sdk --install "build-tools;36.0.0"` (aapt, aapt2,
apksigner, zipalign, d8, dexdump) + `"platforms;android-36"` (android.jar, 27.8 MB, the classic
namespaced Android-Java dialect). Licenses pre-seeded with `cp -r tools/android-clt/licenses sdk/licenses`
(note: licenses live in tools/android-clt/licenses, NOT inside `latest`).

Pipeline (R=repo root, J=sdk/platforms/android-36/android.jar, JDK=tools/jdk/jdk-17.0.20.1+1, B=sdk/build-tools/36.0.0):
1. `gen_app.py` turns `shows.html` into `apkbuild/compact_shows.html` (144 KB: base64 flyer thumbs
   rewritten to the remote jpg URLs, 154 subs) → `ShowData.java` with 36 x 4000-char string chunks
   (chunked assignments, NOT compile-time concatenation, to stay under the 64K dex constant pool).
2. `javac -classpath $J -d apkbuild/cls Main.java ShowData.java` (Android-Java dialect source:
   `package com.punkshows.app;` + namespaced imports like `android.webkit.WebView`).
3. `tools/android-clt/latest/bin/d8 --release --classpath $J --output apkbuild/dex <classes>`
   → classes.dex. `--output` must be an EXISTING DIR or .zip/.jar (never a bare file);
   `--classpath $J` is required or it warns "Type android.app.Activity was not found".
4. `$B/aapt package -v -M apkbuild/AndroidManifest.xml -F apkbuild/app.apk apkbuild/raw` — legacy
   `aapt` (not aapt2) compiles the XML manifest; output flag is `-F`, not `-o`.
5. `zipalign -f 4` → `apksigner sign --key key.der --cert cert.pem` (openssl PEM must be converted
   to PKCS#8 DER first; apksigner 36 rejects `--sig` and PEM).

App behaviour: `android_main(Activity)` makes a `WebView`, probes
`https://seattleareapunkshows.org/` with `java.net.URL.openStream()`; online → `loadUrl()` (live
updates), offline → `loadData("text/html", bundled, null)` (bundled snapshot). So it works
standalone AND updates itself when there is a connection.

API facts verified with javap: WebView has loadUrl/loadData/loadDataWithBaseURL but NO loadHTMLString;
`android.view.ViewGroup.LayoutParams` has only (Context,AttributeSet)/(LayoutParams)/(int,int) ctors
(use MATCH_PARENT); `android.app.Activity` has only a no-arg ctor + addContentView (Activity extends
ContextThemeWrapper, so `activity` is a valid Context); there is NO `android.os.exec` → no shell exec.

HONEST CAVEATS: (1) no Android device here, so the APK is NOT runtime-tested — verified only by
aapt/apksigner/dexdump/zipfile inspection; (2) the manifest + entry-point use the Android-Java/libcore
dialect (android_main, namespaced android.jar APIs) which matches android.jar exactly but libcore was
removed from Android 6+, so this APK targets old Android (≤5) — on modern Android use the PWA/shows.html.

## Next steps
- [x] Cache fill done (PID 570): 422 bands cached, 318 resolved (248 Bandcamp, 70 official
  homepage), 104 unresolved (obscure/cover bands → fall back to bandcamp.com search link).
- [x] Re-rendered: `shows.html` and webapp both show ♪ listen links.
- [x] APK built: `punkshows.apk` 29,005 bytes, signed (route A; no clang needed — d8 replaced
  AOSP clang/aic/so). Still cannot be runtime-tested here (no device).


## Usage
- CLI:  `.venv/bin/python cli.py [--days N] [--genre punk|metal] [--city Seattle] [--listen] [--json]`
- Web PWA: `.venv/bin/python webapp.py` → http://localhost:8000 (dark UI, installable via
  manifest.webmanifest; add-to-home-screen on Android).
- Offline: open `shows.html` (self-contained dark snapshot, regenerated by `snapshot.py`).
- Cache top-up: `.venv/bin/python bandcamp.py [cap] [clear]` (clear retries failed lookups).

## Problems/dead ends
- "Avenged Sevenfold Gojira" style merged names from NCS (no separator in source line) —
  MB still resolves first band; acceptable.
- MB returns homepage when no Bandcamp (e.g. Judas Priest → judaspriest.com) — acceptable per user ask.
