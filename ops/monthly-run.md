# Monthly run: refresh websites and draft next month

Runs on the 18th of each month (scheduled task "Beacon monthly drafts"), so next month's drafts are waiting in the command center by the 20th. The marketer reviews and approves them there; nothing in this run posts anything.

- Command center: https://claude.ai/artifact/G626QaLTCbynVtY1WMb7wj
- Database: read and write it with the `ArtifactData` tool (load it with ToolSearch). Read the artifact once with the `Artifact` tool (`action: "read"`) before uploading photos to it.
- Target month: the calendar month after the run date, unless the prompt names one. Decide the target month before doing anything else, and run the whole procedure once, for that month only.
- Time zone: America/Detroit.

**Setup notes from earlier runs.**
- If the `add_repo` tool is missing, clone with `git clone https://github.com/Tsinawi/beacon`.
- If `python3 -c "import PIL"` fails, create a virtual environment and install Pillow there before running `tools/import_photos.py`.

Work through every active community (`communities` where `active != false`). Keep going if one community fails; report it at the end.

## 1. Read the website

```
NODE_PATH=$(npm root -g) node tools/read_site.js <website> <work>/<slug> 8
```

`pages.json` holds each page's text and image URLs. Pages marked BLOCKED or ERROR: retry once; if still failing, set `harvest.status: "error"` with a short `note` and skip to the next community without touching its drafts.

From the page text, extract only what the site states:
- amenities (community and apartment), floor plans (name, beds, baths, sq ft), neighborhood points, phone, address, office hours
- specials, including their conditions and end dates

Never put prices, fees or school-district claims into the profile's marketing fields. Leave anything the site doesn't say blank.

## 2. Photos and image-only specials

```
python3 tools/import_photos.py <work>/<slug>/pages.json <work>/<slug>/photos --known <work>/<slug>/known.txt
```

Write `known.txt` first: the `hash` of every `media` document for the community, one per line.

Then look at every photo the script kept (build a contact sheet and view it). Keep only real photos of this property and its floor plans. Drop stock photos, people-focused lifestyle images, graphics, maps and other properties' images.

Images with `hint: "flyer"`, and any image that shows text, are often specials. Read the text. A special that appears only in an image still counts: record it with its conditions and end date.

Upload the keepers to the artifact (`Artifact` publish with `asset: true`, `file_paths`, up to 25 per call). Then add a `media` document for each with:
- `communityId`, `assetId`, `kind: "image"`, `caption` (what the photo shows, plainly)
- `shows`: the things clearly visible, using these words where they fit: pool, sundeck, pergola, fitness, clubhouse, lounge, coffee, barkpark, pets, playground, picnic, balcony, patio, kitchen, dining, living, bedroom, bathroom, closet, fireplace, laundry, parking, storage, renovated (only for clearly updated finishes), townhome, exterior, building, entrance, grounds, walkway, outdoor, floorplan. Look at the photo; never infer from the file name. If you aren't sure a building is the clubhouse, say `building`, not `clubhouse`.
- `tag` (`pool`, `fitness`, `clubhouse`, `unit`, `exterior`, `floorplan:<Plan name>`, …)
- `source: "website"`, `sourceUrl`, `sourceFile`, `hash`, `addedAt`

## 3. Update the community profile

`update` the community document, pinned to the version you read, with the extracted fields plus:
- `specials`: a list of `{text, seenAt, source, endsOn}`. Drop specials no longer on the site.
- `harvest`: `{status: "ok", lastRun, note, pages}`

Do not overwrite fields the site doesn't cover: `hashtagSet`, `links`, `audience`, `voice`, `logoAssetId`, `logoTone`, `color`, `defaultCorner`, `short`.

Keep a list of what changed (new photos, new or ended specials, amenity or floor plan changes) for the summary.

## 3b. Refresh the area (quarterly)

If the community's `area.fetchedAt` is missing or more than 90 days old:

```
python3 tools/nearby.py "<address>" <work>/<slug>/area.json --name "<community name>"
```

The tool finds the community by street address, or by name when that lands within 8 miles of the address's town. Check that `center.matched` names the right town. If it can't place the community, or places it wrong, skip the area update and say so in the summary. You can rerun it with `--lat`/`--lon` when you know the spot.

Read the place list before saving. Drop anything private, members-only, school- or church-affiliated, a subdivision or homeowners' association, or obviously closed. Then `update` the community with `{area: <file contents>}`.

`areaNotes` is text the marketer pasted (for example from Apartments.com). Use it as background, but never overwrite it.

## 4. Draft the target month

Read `settings/brand` (voice, cadence, mix, timeSlots) and every post for the community from 4 months before the target month through the end of the target month.

- If approved or posted posts already exist in the target month, keep them and plan around them.
- If drafts already exist, leave them. Only fill weeks that have fewer posts than the cadence.

Plan 3–4 posts per week, spread over different weekdays, following the content mix. Every post date must fall inside the target month. A week that runs into the next month gets only the posts dated in this month; the next run covers the rest.
- **Holiday:** real holidays in the month.
- **Fun day:** widely known national days and seasonal moments. No politics, religion or elections.
- **Amenity:** one amenity per post.
- **Floor plan:** one plan per post.
- **Local spotlight:** one real place from `area.places` or `areaNotes`, by its exact name, with its type and "about N miles away".
  - Don't invent hours, menu items, prices or events. Invite people to share their favorite instead.
  - Prefer local independents over national chains, and don't feature the same place twice within 6 months.
  - Use the branded graphic (`assetId: null`) with the place name as `overlay.label` (2–4 words). The command center adds the "Local spotlight" map-pin chip.
  - Set `linkKey: "neighborhood"`.
- **Video tour:** while Reels from photos are not built yet, write the caption and set `needsData: "Upload the walkthrough video (vertical, under 90 seconds works best for Reels)."`

**Fresh content first. No repeats inside 3 months.**
- Prefer amenities, floor plans and photos that are new this month or have not appeared in the last 4 months.
- Don't feature the same amenity or floor plan, or use the same photo, if the community posted it in the 3 months before the target month or earlier in the target month.
- When fresh amenity or floor plan topics run out, fill those slots with fun days, seasonal moments or neighborhood posts drawn from the profile instead of repeating. The content mix is a target, not a quota.
- Once something is more than 3 months old, it can come back with a new caption and, when there is one, a different photo.

**Check every draft before saving.** These mirror the command center's checks, which block approval when they fail:
- The photo shows the subject (above), and a floor plan flyer matches the plan named.
- Every amenity the caption mentions appears in the profile's `amenities` from the website. A photo showing something (like a coffee bar) isn't enough: if the website doesn't list it, don't claim it.
- Floor plan bedrooms, bathrooms and square footage match the profile exactly.
- No offers or "free" language unless a current special covers the post date.
- Pool posts outside May–September only if the caption looks ahead to summer; prefer another amenity.
- Don't use the same photo twice in a month, or repeat an amenity or plan within 90 days.

**Writing rules.** These are the same as the command center's generator:
- Fair housing: never describe who the ideal resident is. Don't mention families, children, age groups, students, singles, couples, religion, national origin, disability, or "safe neighborhood". Describe the property, amenities and events. Say "primary bedroom". Never mention schools, school districts or places of worship, even when area notes do.
- Use only facts from the profile. If a fact is missing, set `needsData` to what is missing and use a [bracketed placeholder].
- No prices unless they are in a current special. Mention a special only if it runs through the post date (`endsOn` on or after the post date).
- Captions are 40–120 words with 1–2 emoji, and end with a soft call to action. No URLs in captions.

**Fields for each post** (`posts` collection, new document id `<date>-<short>-<type>[-n]` in lowercase):
- `communityId`, `date`, `type`, `title`, `caption`, `gbpCaption: ""`, `status: "draft"`, `needsData`, `createdBy: "monthly-run"`, `updatedAt`
- `time`: `settings.timeSlots[(communityIndex + dayOfMonth) % timeSlots.length]`. `communityIndex` is the community's position when active communities are sorted by name.
- `hashtags`: the community's `hashtagSet` plus 1–2 tags specific to the post
- `linkKey`: amenity → `amenities`, floorplan → `floorplans`, video → `tour`, local → `neighborhood`, everything else → `home`
- `platforms`: Facebook and Instagram always; Google for amenity, floor plan and special posts
- `assetId` and `mediaKind: "image"`: the chosen library photo. **The photo must show the post's subject**: its `shows` list has to include it (a covered parking post needs a photo with `parking`, a pet post one with `pets` or `barkpark`). Look at the photo before choosing it. If no library photo shows the subject, use the branded graphic (`assetId: null`) with the amenity as `overlay.label`. Never stand in a general exterior or lawn shot. Use a floor plan image for floor plan posts when one exists. Before uploading a new floor plan flyer, cover its phone-number line with the panel's own blue (the flyers' numbers don't match the websites); keep the address and website lines. Tag every floor plan flyer `floorplan:<Plan name>` in `media`: the command center shows those images whole, with no logo or Equal Housing overlay, because the flyer already has both. Holiday and fun-day posts use the branded graphic (`assetId: null`).
- `overlay`: `{corner: community.defaultCorner || "tr", label}`. Give holiday, fun-day and special posts a 2–4 word headline; leave other labels empty. Amenity posts with a photo get an amenity icon automatically, picked from the post title and photo, so use plain amenity words in titles ("Pool and sundeck spotlight", "Bark park spotlight"). To force one, set `overlay.icon` to a key from `ICONS` in the command center, or `"none"`. Photo posts rotate through five 4:5 layouts automatically (blurred fill, color-matched bands, brand panel, two-photo stack, swipe carousel), so leave `overlay.layout` unset. Give each amenity two or more library photos when you can, so its two-photo stack posts have a second image.

Write with `batch` (up to 50 writes per call).

## 5. Summary (the run's final message is emailed to the marketer)

End with a short plain-text summary:

```
Drafts for <Month YYYY> are ready to review: <link>

Per community: <name>: <n> drafts (<n> need info) · website: <changes or "no changes"> · <n> new photos
Specials: <new / ended / none>
Needs you: <communities that failed to read, posts that need info, missing tracking links>
```

Keep it scannable. No apologies or filler.
