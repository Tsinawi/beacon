# Beacon Social

Social media planning, approval and (soon) auto-publishing for Beacon Management's 30–40 apartment communities.

**Command center:** https://claude.ai/artifact/G626QaLTCbynVtY1WMb7wj (private to the owner)

## How it fits together

| Piece | Lives in | Status |
|---|---|---|
| Command center (calendar, editor, approvals, community profiles, photo library) | `app/command-center.html`, published as a Claude artifact | Built |
| Database (communities, posts, media, settings) | The artifact's built-in database | Seeded |
| AI captions and rewrites | Claude, called from the page | Built |
| Branded image compositing (corner badge, headline, Equal Housing Opportunity line) | Canvas in the page; final JPG saved on approval | Built |
| Website reader (source of truth for amenities, floor plans, specials, photos) | Scheduled Claude task that writes to the database | Next |
| Hourly publisher (Facebook, Instagram) | `tools/publish_meta.py`, run by `ops/publish-run.md` in the locked-down publisher environment; Meta system-user token held as a proxy-injected credential | Built, dry run; Google not yet |

The community website is the source of truth. There is no PMS integration.

## Data model

- `communities/{slug}`: `name, short, hashtagSet, links{home,floorplans,amenities,tour,gallery,neighborhood} (tracked URLs), logoTone (auto|original|white|black), website, city, state, color, audience, voice, phone, address, amenities[], floorPlans[{name,beds,baths,sqft,notes}], specials[{text,seenAt,source}], neighborhood[], area{source,fetchedAt,center,radiusMiles,places[{name,category,type,miles,osm}]} (OpenStreetMap), areaNotes (pasted, e.g. from Apartments.com), logoAssetId, defaultCorner, active, harvest{status,lastRun,note,requestedAt}`
- `posts/{id}`: `communityId, date (YYYY-MM-DD), time (HH:MM, rotated from settings.timeSlots), type (amenity|floorplan|holiday|funday|local|video|special|other), title, caption, gbpCaption, hashtags, linkKey (home|floorplans|amenities|tour|gallery|neighborhood|"" — defaults by type when absent), platforms{facebook,instagram,google}, assetId, mediaKind (image|video), overlay{corner,label,icon,iconLabel,layout,assetId2}, status (draft|approved|posted|held|failed), needsData, finalAssetId (4:5, 1080×1350), finalAssetIds ([slide1, slide2] for carousel layout), finalLayout (blur|match|panel|stack|carousel|full, frozen on approval), finalGoogleAssetId (4:3, 1200×900), approvedAt, postedAt, error, createdBy, aiCheck{at,assetId,captionSig,photoShows,photoMatches,issues[]}`
- `media/{id}`: `communityId, assetId, kind, caption, shows[] (what is visible; drives photo checks), tag, source (website|upload|onedrive), addedAt, checkedAt`
- `settings/brand`: `company, voice, cadence, timeSlots[], mix{type: weight}, eho, extraPhrases[], publishing{meta,google,harvester,publisher}`

Access rules: anyone the page is shared with can read; only Editors and the owner can write. `control/publishing` (pause, dry run, approver, late window, cap, connection status) is writable by the owner only.

- `control/publishing`: `paused, dryRun, approverId, lateHours, maxPerRun, meta{status,name,checkedAt}`
- `publishLog/{id}`: `at, postId, communityId, title, platforms, result, note`
- `communities/{slug}.meta`: `pageId, igUserId` (Meta connection)
- Posts also carry `approvedBy, approvedSig (SHA-256 of the canonical approved content), approvedLink, postedIds, dryRunAt`.

## Publisher contract (for the scheduled task)

1. Find posts where `status == "approved"` and `date`/`time` is in the past.
2. If the caption mentions a special, re-read the community website. If the special has changed or is gone, set `status: "held"` with an `error` explaining why.
3. Resolve the link: `communities/{communityId}.links[linkKey]` (linkKey defaults by type: amenity→amenities, floorplan→floorplans, video→tour, everything else→home).
   - If `finalAssetIds` has two images, the 4:5 layout is a swipe carousel: post both, in order, as a Facebook multi-photo post and an Instagram carousel. Otherwise use `finalAssetId`.
   - Facebook: `finalAssetId` (or the video) with `caption + "\n\n" + link + "\n\n" + hashtags`.
   - Instagram: `finalAssetId` (or the video as a Reel) with `caption + "\n\n" + hashtags`. No link; captions can't hold one.
   - Google Business Profile: `finalGoogleAssetId` with `gbpCaption || caption`, no hashtags, and a "Learn more" call to action pointing at the link.
4. Set `status: "posted"` and `postedAt`, or `status: "failed"` and `error`.

## Seed data

`data/seed/` holds the documents first loaded into the database: two pilot communities, brand settings and November 2026 drafts.

## Credits

Amenity icons are from [Lucide](https://lucide.dev), ISC License, Copyright (c) Lucide Icons and Contributors.

Nearby places come from [OpenStreetMap](https://www.openstreetmap.org/copyright) via its Nominatim search. Map data © OpenStreetMap contributors, ODbL 1.0. Apartments.com blocks automated access and its terms prohibit scraping, so its area details are pasted in by hand (`areaNotes`).
