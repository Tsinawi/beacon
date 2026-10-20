# Monthly run: refresh websites and draft next month

Runs on the 18th of each month (scheduled task "Beacon monthly drafts"), so next month's drafts are waiting in the command center by the 20th. The marketer reviews and approves them there; nothing in this run posts anything.

- Command center: https://claude.ai/artifact/G626QaLTCbynVtY1WMb7wj
- Database: read and write it with the `ArtifactData` tool (load it with ToolSearch). Read the artifact once with the `Artifact` tool (`action: "read"`) before uploading photos to it.
- Target month: the calendar month after the run date, unless the prompt names one.
- Time zone: America/Detroit.

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
- `tag` (`pool`, `fitness`, `clubhouse`, `unit`, `exterior`, `floorplan:<Plan name>`, …)
- `source: "website"`, `sourceUrl`, `sourceFile`, `hash`, `addedAt`

## 3. Update the community profile

`update` the community document, pinned to the version you read, with the extracted fields plus:
- `specials`: a list of `{text, seenAt, source, endsOn}`. Drop specials no longer on the site.
- `harvest`: `{status: "ok", lastRun, note, pages}`

Do not overwrite fields the site doesn't cover: `hashtagSet`, `links`, `audience`, `voice`, `logoAssetId`, `logoTone`, `color`, `defaultCorner`, `short`.

Keep a list of what changed (new photos, new or ended specials, amenity or floor plan changes) for the summary.

## 4. Draft the target month

Read `settings/brand` (voice, cadence, mix, timeSlots) and every post for the community from 4 months before the target month through the end of the target month.

- If approved or posted posts already exist in the target month, keep them and plan around them.
- If drafts already exist, leave them. Only fill weeks that have fewer posts than the cadence.

Plan 3–4 posts per week (Monday–Sunday weeks that start in the target month), spread over different weekdays, following the content mix:
- **Holiday:** real holidays in the month.
- **Fun day:** widely known national days and seasonal moments. No politics, religion or elections.
- **Amenity:** one amenity per post.
- **Floor plan:** one plan per post.
- **Video tour:** while Reels from photos are not built yet, write the caption and set `needsData: "Upload the walkthrough video (vertical, under 90 seconds works best for Reels)."`

**Fresh content first.**
- Prefer amenities, floor plans and photos that are new this month or have not appeared in the last 4 months.
- Repeat an amenity, plan or photo used 3–4 months ago only when nothing fresh is left, and write a new caption for it.
- Never use the same photo twice in one month for the same community.

**Writing rules.** These are the same as the command center's generator:
- Fair housing: never describe who the ideal resident is. Don't mention families, children, age groups, students, singles, couples, religion, national origin, disability, or "safe neighborhood". Describe the property, amenities and events. Say "primary bedroom".
- Use only facts from the profile. If a fact is missing, set `needsData` to what is missing and use a [bracketed placeholder].
- No prices unless they are in a current special. Mention a special only if it runs through the post date (`endsOn` on or after the post date).
- Captions are 40–120 words with 1–2 emoji, and end with a soft call to action. No URLs in captions.

**Fields for each post** (`posts` collection, new document id `<date>-<short>-<type>[-n]` in lowercase):
- `communityId`, `date`, `type`, `title`, `caption`, `gbpCaption: ""`, `status: "draft"`, `needsData`, `createdBy: "monthly-run"`, `updatedAt`
- `time`: `settings.timeSlots[(communityIndex + dayOfMonth) % timeSlots.length]`. `communityIndex` is the community's position when active communities are sorted by name.
- `hashtags`: the community's `hashtagSet` plus 1–2 tags specific to the post
- `linkKey`: amenity → `amenities`, floorplan → `floorplans`, video → `tour`, everything else → `home`
- `platforms`: Facebook and Instagram always; Google for amenity, floor plan and special posts
- `assetId` and `mediaKind: "image"`: the chosen library photo. Use a floor plan image for floor plan posts when one exists. Holiday and fun-day posts use the branded graphic (`assetId: null`).
- `overlay`: `{corner: community.defaultCorner || "tr", label}`. Give holiday, fun-day and special posts a 2–4 word headline; leave other labels empty.

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
