# Before full rollout

Projects to finish before Beacon Social handles every post for every community (50+ properties). Nothing here is built yet unless it says so.

## 1. Local spotlight images

**Goal:** every local spotlight gets a real-looking, rights-safe image, with no manual sourcing. At 50+ properties nobody can ask businesses for photos or hand-pick images.

**Not allowed:** Google Images, Google Maps / Places photos, Yelp or business photos without permission.

**Plan, in order of preference for each post:**
1. **Wikimedia Commons photo, found automatically.** Follow the place's OpenStreetMap → Wikidata link, check the license allows commercial use, and add the credit line to the caption. Expect roughly a third to half of places to have one (parks, landmarks, downtowns more than cafés).
2. **Property photo + "nearby" panel** (mockup C).
3. **Distance card** (mockup A), with no photo needed.
4. About once a month, a **3-spot roundup** (mockup B), as a carousel cover with one slide per place.

**Also:** rank places that have a usable photo higher when picking spotlights.

**Mockups:** `docs/mockups/local-spotlight/` (A distance card, B roundup, C photo + nearby). They were made from Glens data with `make_mockups.py`, and are map-free on purpose.

**Open decisions:**
- Which designs to keep; colors, fonts and layout tweaks.
- Whether to add a real street map later. That needs a map data source reachable from the drafting environment and storing each place's coordinates; `tools/nearby.py` keeps only distance today.

## 2. Holiday and fun-day graphics (Canva)

**Goal:** no blank branded graphics. The marketer designs one Canva graphic per holiday, and the tool reuses it across all properties.

**Plan:**
- Make one **shared Beacon holiday and fun-day calendar** for all communities, instead of picking per community. That's 3–5 graphics a month and about 40–50 a year, reused every year. Nov–Dec 2026 drafts needed 18 graphics under per-community picking; a shared calendar cuts that to about 8.
- Store the graphics in a **Seasonal library** shared across communities, tagged by holiday, and alternate between versions year to year.
- The tool adds the community logo (with automatic tone) and the Equal Housing line.
- Canva export: PNG at 1080 × 1350. Keep the top-right corner (about 250 × 250 px) and the bottom strip (about 80 px) clear.
- The monthly run flags any holiday in next month's drafts that has no graphic, in the summary on the 18th.
- Generic seasonal posts ("Cozy fall weekend", "Thank you, residents") use a seasonal property photo with a headline instead of a designed graphic. That needs a season tag on photos.
- No people in holiday art. Decide how to handle religious holidays (for example "Happy Holidays").

**Open decisions:**
- Should the tool add the logo, or should graphics stay clean?
- The final holiday list: draft a full year of 40–50 days to cut down.
- Start month.

## 3. Publisher reliability

- The 10:05am run on 2026-11-13 didn't post (Bradley was posted by hand at 10:18). A check-in task fired 43 minutes late the same day.
- The task schedule was set to `CRON_TZ=America/Detroit 5 10-17 * * *`. Confirm in **Scheduled → Beacon publisher** that it shows Detroit time and see what the run history says.
- Watch the next approved post. Post by hand if the run misses it.

## 4. Other items carried over

- Brand panel layout is retired for now (code kept).
- Tracking links per community (still empty), audience notes, walkthrough videos.
- Reels from website photos; weekly summary email.
- Google Business Profile publishing (deferred; Meta only for now).
- Another tool is also posting to the Glens pages (for example 9:59am on 2026-11-13). Decide whether to turn it off for pilot pages.
- Meta token renewal around 2027-01-04 (expires about 2027-01-11).
