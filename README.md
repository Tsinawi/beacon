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
| Hourly publisher (Facebook, Instagram, Google Business Profile) | Scheduled Claude task, API tokens kept as environment secrets | Blocked on Meta app review and Google API access |

The community website is the source of truth. There is no PMS integration.

## Data model

- `communities/{slug}`: `name, short, website, city, state, color, audience, voice, phone, address, amenities[], floorPlans[{name,beds,baths,sqft,notes}], specials[{text,seenAt,source}], neighborhood[], logoAssetId, defaultCorner, active, harvest{status,lastRun,note,requestedAt}`
- `posts/{id}`: `communityId, date (YYYY-MM-DD), time (HH:MM), type (amenity|floorplan|holiday|funday|video|special|other), title, caption, gbpCaption, hashtags, platforms{facebook,instagram,google}, assetId, mediaKind (image|video), overlay{corner,label}, status (draft|approved|posted|held|failed), needsData, finalAssetId, approvedAt, postedAt, error, createdBy`
- `media/{id}`: `communityId, assetId, kind, caption, source (website|upload|onedrive), addedAt`
- `settings/brand`: `company, voice, cadence, defaultTime, mix{type: weight}, eho, extraPhrases[], publishing{meta,google,harvester,publisher}`

Access rules: anyone the page is shared with can read; only Editors and the owner can write.

## Publisher contract (for the scheduled task)

1. Find posts where `status == "approved"` and `date`/`time` is in the past.
2. If the caption mentions a special, re-read the community website. If the special has changed or is gone, set `status: "held"` with an `error` explaining why.
3. Post `finalAssetId` (or the video `assetId`) with the caption and hashtags to each enabled platform. Google gets `gbpCaption || caption`, without hashtags.
4. Set `status: "posted"` and `postedAt`, or `status: "failed"` and `error`.

## Seed data

`data/seed/` holds the documents first loaded into the database: two pilot communities, brand settings and November 2026 drafts.
