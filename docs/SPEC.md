# 12 Frames Per Week: site and sending pipeline spec (updated 2026-10-26)

Replaces the old Mailchimp-based plan. The site and the email come from the same post data.
Repo: github.com/shakadunk/12fpw. Domain: 12fpw.com (currently serving the Mailchimp archive).

## Status
- DONE (demo, live on Vercel at 12fpw.vercel.app): black site with SCROLL, GRID and CALENDAR views, home page = latest post, post pages, light/dark toggle, ARCHIVE dropdown in the header, scroll-up bar (ARCHIVE / TOP / LIGHT) on every page, signup form parked (hidden everywhere until a new spot is chosen), `scripts/add-post.mjs` to make a post from 12 images + text. Demo posts reuse 12 sample images; delete them before launch.
- WORKFLOW: Shaka describes a change, Claude confirms details, edits, tests, and pushes to the GitHub repo; Vercel redeploys automatically. Claude can push to shakadunk/12fpw (the Claude GitHub App is installed on the repo).
- TO BUILD: backfill of the old posts, private upload page, email rendering, sending via Resend, signup endpoint, moving 12fpw.com to Vercel.

## Old template (from Week 3 and Week 4)
- White background, one centered column about 600px wide, Helvetica/Arial.
- Logo top-left: "12 / FRAMES / PER WEEK", bold, three stacked lines, with the "1" in 12 hanging to the left of FRAMES and PER (deliberate kerning). The logo was a PNG. The website no longer uses it (see Header below); white and black transparent copies are kept in assets/ in case they are wanted for the email or elsewhere.
- Centered "Week N" in small gray with a short thin rule under it.
- Body text about 15px, line height about 1.7, short paragraphs, then a sign-off such as "In blue," / "SD" on separate lines.
- 12 images stacked at full column width, uncropped, no captions.
- Footer: "12FPS 2024", a Boston postal address, an underlined Unsubscribe link.
- Week number is week of the year.

## Design (new)
- Pure black (#000) background, white text, full-color images floating on black. Light/dark toggle kept as a secondary option.
- Each post = "Week N" label with rule, text, then exactly 12 images. One of the 12 is the hero.
- SCROLL: newest first, infinite scroll, thin horizontal rule between posts.
- GRID: Instagram-style grid of hero images (3 columns, square crops), each labelled with its week number. Click opens the post.
- CALENDAR: the GRID, split into months with horizontal dividers.
- Home page = the most recent post (same layout as a post page, no back button). Older weeks opened from the archive have a "← Archive" back link at the top, above the Week heading.
- Header: at the left the site name as plain text, "12 FRAMES PER WEEK" in small all-caps, same size, spacing and colour as the nav (12FPW on phones, under 720px wide), always a link to the home page, on every page. The stacked logo image was removed from the site (2026-10-26). At the right ARCHIVE and LIGHT/DARK. SUBSCRIBE was removed (Shaka will find another place for the signup form). ARCHIVE is a dropdown with SCROLL / GRID / CALENDAR: on the archive page it switches the view in place, on any other page it opens the archive in that view. On desktop (mouse) the menu opens when the pointer rests on ARCHIVE (after about 80ms, so a pointer sweeping past does not open it) and closes about 250ms after the pointer leaves; clicking ARCHIVE while it is open from hovering pins it open until Esc or a click elsewhere. Touch devices tap to open, as before, and the keyboard (Enter / Esc) works. The archive page has no title row and no inline view buttons any more (the "ARCHIVE (12)" label was removed).
- Footer: on the home page the footer is just today's date at the bottom right (e.g. 26 OCTOBER 2026, day number always two digits), shown in small uppercase type and filled in live from the visitor's device, so it rolls over at midnight if the page stays open. No copyright line, because most of the images are not Shaka's. The archive and post pages keep the older footer (site name plus an Archive link; the Subscribe link was removed along with the parked signup form).
- A post's calendar month comes from the Thursday of its ISO week (Week 1 of 2025 starts Dec 30, 2024 but files under January 2025). A post's issue.json can carry a real "date" to override.

## Email
- Colorless on purpose: just text and images, no background or text colors set, so it follows each reader's light/dark setting.
- A black PNG logo would vanish in dark mode, so use live text for the name in the email, or switch to a new logo. The website now uses a plain-text name, so the same plain text works in the email too.
- Footer keeps the postal address and an unsubscribe link (both legally required).

## Process
1. Shaka submits raw text + 12 images on a private, password-protected upload page on the site.
2. The pipeline builds the post, publishes a preview, and sends a test email to Shaka.
3. Shaka approves. Nothing reaches subscribers before that.
4. On approval the post goes live and the email goes to subscribers.
5. The email uses the site's hosted image URLs. No Mailchimp.

## Sending
- Expected list: under 100 subscribers.
- Resend free plan: 3,000 emails/month, 100/day cap, can also receive email. Check audience and contact limits at setup.
- Past 100 subscribers: upgrade or switch (Brevo free is 300/day with its branding; Amazon SES is about $0.16 per 1,000). Keep the sending code provider-agnostic.
- Sending from 12fpw.com needs SPF/DKIM records.
- The signup form (currently hidden everywhere) adds people to the provider's list; the provider handles unsubscribe links.

## Archive backfill (about 60 posts)
- Week 1 was in 2024, and posts ran through the first few weeks of 2025.
- Plan: Shaka has the original images grouped by week in Adobe Bridge. He uploads zips (about 8 to 10 weeks each; start with a batch of 3 or 4) with one folder per week named `<year>-w<NN>`, 12 images numbered in order, a `text.txt`, and an optional `hero.txt` holding the hero image number. Claude processes each batch with `scripts/add-post.mjs`, pushes, and the site fills in.
- Fallback: the Mailchimp archive pages block automated readers, but Safari "Print as PDF" works: a script can pull the text and the 12 images from each PDF (tested on Week 3). Extracted images are only the emailed size (about 750px wide), so originals are better.
- PDFs say "Week N" but not the year. Posts were weekly from Week 1 of 2024, so year plus week determines the date. Ask about any skipped weeks.
- Old Mailchimp links will break once 12fpw.com moves; that is accepted as long as the posts are in the new archive.

## Technical notes
- Uploads must go straight to storage, not through a serverless function: Vercel's per-request size limit (about 4.5 MB, to verify) is too small for 12 photos.
- Source of truth is the GitHub repo (issues/<year>-w<week>/); Vercel redeploys on push. If the portal needs to publish without a git push, fall back to Vercel Blob with the site reading from it.
- Shaka does not want to install Claude (Claude Code) on his work computer, so everything must run in the browser and on Vercel. The cloud sandbox cannot reach the npm registry, so the portal and sending code should use only what Node already includes, or be built so Vercel installs any packages at deploy time.
- Browser tests live in tests/ (Python + Playwright; run `python3 tests/test_nav.py`, `python3 tests/test_footer.py` and `python3 tests/test_seam.py` after building; test_seam measures the frosting over a flat grey and fails if a seam appears between the bar and the menu). They cover the header dropdown, the scroll-up bar, TOP, the three archive views, the home page, older weeks, phones, reduced motion, and the live date footer.
- Repo size: about 2 MB per post after resizing, so 60 posts is roughly 120 MB. Commit only resized images.

## Scroll-up bar (replaces the earlier VIEW / TOP archive bar; 2026-10-26)
- On every page (home, archive, week pages): scrolling down hides the header and nothing replaces it; scrolling back up slides in ONE frosted band across the whole top of the screen. It is not shown while the header is still on screen. Hide delay: scrolling down does not hide it at once; it lingers for about 1 second first. Scrolling back up during that second cancels the countdown (the bar stays), a fresh scroll down starts a fresh 1 second, and continuous scrolling down does not keep pushing the hide back. While a mouse rests on the bar or its menu the bar stays; the 1 second countdown starts again when the mouse leaves (only if the bar was on its way out). If the menu is open it stays open during the delay and closes when the bar hides. Reaching the top of the page hides it immediately, because the header is back on screen.
- Left: "12 FRAMES PER WEEK" in plain all-caps text, same size and colour as the buttons, and a link to the home page (underlined only on hover). On phones (under 720px wide) it shows "12FPW" instead. Right: ARCHIVE, TOP, LIGHT/DARK in that order (LIGHT in the same far-right spot as in the header).
- ARCHIVE in the bar drops down SCROLL / GRID / CALENDAR (current view in full white, the others dimmed), the same menu as in the header, including hover-to-open on desktop.
- Look: the band is about 30% tint (black in the dark theme, white in the light theme) with a 14px blur, feathered along its bottom edge so it dissolves into the photo; about 37px tall plus the feather. The band keeps this single depth at all times. When the ARCHIVE menu is open, the bar and the menu are ONE continuous frosted element: the bar's own layer is extended downward under the menu column, with a mask that is the band unioned with a feathered rectangle under the menu, so there is a single blur and a single tint and no overlap (it is the same 30% tint and 14px blur in both themes). History: an earlier version used a separate patch layer behind the menu; where it overlapped the bar it made a denser stripe (about 11 grey levels over the band's tint) that read as a separate box with a gap, so it was merged on 2026-10-26. Browsers without CSS mask compositing fall back to the separate patch. The menu has no solid panel of its own.
- TOP glides back to the top (ease in-out, about 0.45s for a short climb up to a cap of 1.4s), keeps the current view, any wheel/touch/key/mouse press stops the glide, reduced-motion readers get an instant jump.
- Earlier iterations (for reference): a full-width bar with VIEW / TOP centred over the photos, then two separate frosted patches. Shaka chose the single band.
- Earlier: the whole band deepened when the menu opened; Shaka found that too heavy, so the deeper blur is now only behind the menu.
- REVISIT once the backfill starts: with 60+ posts, check that the bar's behavior and size feel right.

## Still open
- Revisit the scroll-up bar (see above) once the backfill is in
- Where the signup form goes (parked; hidden on every page until Shaka picks a spot)
- Any skipped weeks in 2024 and early 2025
- How to get the 60 posts' content out (PDF per post, or original files)
- Approval UX: preview link plus an Approve button on the upload page
- Logo: the site now uses plain text only (no logo image). Decide whether the email keeps the old stacked logo, uses the same plain text, or gets a new mark
