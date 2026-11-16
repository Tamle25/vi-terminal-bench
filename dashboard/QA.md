GATE: OPEN 32 (rounds used up)

# Dashboard verification

11 backend/HTTP tests passed. JavaScript syntax checked. The actual HTTP actions preview, backend validation, budget synchronization and report regeneration completed. Rebuilt trial rows equal the 36-row baseline exactly. No model API calls were made during QA.

Screenshots are stored locally in `.dashboard/shots/` (ignored). Chrome headless ran through the skill scripts on the local QA server. Paid actions were denied by the server during all browser checks.

The design gate is configured for presentation sites. The remaining findings include its required full-screen marketing hero, one section per viewport, marketing CTA on a price card, photographs in a results table, a scroll moment, headline vocabulary in Vietnamese, and a centered landing-page container instead of a dashboard sidebar. These are recorded as open; no waiver was used and no passing design gate is claimed. Contrast, field labels, keyboard focus, chart bounds and mobile result readability were corrected.

Kind: software application. Palette: white/forest green, Segoe UI/Cascadia Code. The real benchmark table and EN/VI bars are the visual material. Voice: concise Vietnamese technical UI. No photographs, invented facts, customer claims, hosted deployment, or third-party network assets.

## Open gate findings

- **hero-fill** (1440): div#overview > div.stats-grid > article.stat:nth-of-type(1) "Tỷ lệ đạt ↗ 97,22% 35 đạt · 1 không đạt" — the next section shows on the first screen: it starts at 273px on a 900px screen (the hero ends at 190px)
- **nav** (1440): (the first screen) — no nav bar across the top of the first screen (a header with the brand, the section links and the main action)
- **cta** (1440): div#overview > div.stats-grid > article.stat:nth-of-type(4) "Chi phí lần chạy $ $ 0,1139 Ước tính tok" — 1 priced card with no action in or under it
- **copy-headings** (1440): h2#chart-title "Kết quả theo tác vụ" — "Kết quả theo tác vụ" names no product, part, place or section (2 headings like it; at most one brand line per page) (and 1 more like it: "Cấu hình đánh giá")
- **heading-scale** (1440, 390): div#stat-pass "97,22%" — the figure "97,22%" is set at 31px, larger than the section headings (h2 14px); 2 more like it
- **moment-none** (1440): (the page) — a software page (--type) deals no moment: every kind carries one, two on a long page (moments.md)
- **hero-screen** (1440): main#main > div.page-heading "VIETNAMESE LOCALE-AWARE EVALUATIONTổng q" — the hero ends at 190px on a 900px screen, 711px above the fold: it ends at the fold, 1px either way (SR-1)
- **hero-screen** (1440): div#overview "Hoàn tấtstage11-development-001Lần chạy " — 682px of the next section shows on the first screen (from 219px on a 900px screen): nothing below the hero shows at load (SR-1)
- **section-height** (1440): main#main > footer.footer "VN Terminal Bench / Development · chưa r" — the section is 64px tall (0.1 screens), 837px short of one screen (900px): every section after the hero is one screen or two, 2px either way (SR-2)
- **section-height** (1440): div#overview "Hoàn tấtstage11-development-001Lần chạy " — the section is 1495px tall (1.7 screens), 305px short of two screens (1800px): every section after the hero is one screen or two, 2px either way (SR-2)
- **one-section** (1440): h1#page-title "Tổng quan benchmark" — the screen at scroll 0px (stride 0) shows 89px of section 1 and the heading of section 1 whole and the content of 2 sections, over 24px each beside section 2: a screen shows one section (another may peek 8px, 24px WARN) (SR-4)
- **one-section** (1440): main#main > footer.footer "VN Terminal Bench / Development · chưa r" — the screen at scroll 877px (the top of section 3) shows 63px of section 3 beside section 2: a screen shows one section (another may peek 8px, 24px WARN) (SR-4)
- **one-section** (1440): div#overview "Hoàn tấtstage11-development-001Lần chạy " — a <div> sits directly in <main>: every part of <main> is a <section> (SR-4)
- **one-heading** (1440): h2#config-title "Cấu hình đánh giá" — the section holds 3 h2 headings: one per section, first in its .wrap (SR-5)
- **container-edges** (1440): main#main > div.page-heading "VIETNAMESE LOCALE-AWARE EVALUATIONTổng q" — the content of section 1 runs 262px from the left and 38px from the right (read from its outermost blocks: no .wrap): 262 and 38px are not one margin; the margin is 64-120px at 1440px (one container, equal margins, 2px either way) (SR-6)
- **container-edges** (1440): div#overview "Hoàn tấtstage11-development-001Lần chạy " — the content of section 2 runs 262px from the left and 38px from the right (read from its outermost blocks: no .wrap): 262 and 38px are not one margin; the margin is 64-120px at 1440px (one container, equal margins, 2px either way) (SR-6)
- **container-edges** (1440): main#main > footer.footer "VN Terminal Bench / Development · chưa r" — the content of section 3 runs 262px from the left and 38px from the right (read from its outermost blocks: no .wrap): 262 and 38px are not one margin; the margin is 64-120px at 1440px (one container, equal margins, 2px either way) (and 1 more like it: "Workspace / Tổng quanLoc") (SR-6)
- **container-edges** (1440): a.skip-link "Đến nội dung" — a <a> at the top of the page, outside header.nav, main, footer.closing and nav.actionbar (SR-6)
- **container-edges** (1440): aside.sidebar "vn_Terminal BenchVietnamese evaluation W" — a <aside> at the top of the page, outside header.nav, main, footer.closing and nav.actionbar (SR-6)
- **container-edges** (1440): div.shell "Workspace / Tổng quanLocalVN VIETNAMESE " — a <div> at the top of the page, outside header.nav, main, footer.closing and nav.actionbar (and 3 more like it: "VIETNAMESE LOCALE-AWARE ", "Hoàn tấtstage11-developm", "VN Terminal Bench / Deve") (SR-6)
- **container-edges** (1440): h2#config-title "Cấu hình đánh giá" — the h2 starts 770px right of the container's left: every h1 and h2 starts on it, 2px either way (SR-6)
- **container-edges** (1440): section.panel.results-panel > div.table-filters > label.filter-control:nth-of-type(2) > span "Ngôn ngữ" — 1 text block starts on a left line at x 623, 361px from the container's left: text starts on the container's left, or on one split line (x 747, 844, 941) (and 5 more like it: x 296, x 285, "Kết quả theo tác vụ") (SR-6)
- **row-lines** (1440): div#comparison-chart > div.chart-inner > div.chart-body "B001B002B003B004B005B006" — a row of 6 items: its first item starts at 327px, its column's left line at 263px; its last item ends at 964px, its column's right line at 988px (2px either way) (SR-7)
- **hero-fill** (390): div#overview > div.overview-toolbar "Hoàn tất stage11-development-001 Lần chạ" — the next section shows on the first screen: it starts at 326px on a 844px screen (the hero ends at 303px)
- **flush** (390): main#main > div.page-heading > a.button.primary "＋ Chạy benchmark" — its button sits 0px above the lower edge of div.page-heading, where the ground changes to div.overview-toolbar
- **flush** (390): select#run-select "Baseline · 6 tác vụ Dựng lại baseline · " — its last line sits 0px above the lower edge of div.overview-toolbar, where the ground changes to article.stat:nth-of-type(1)
- **flush** (390): div#stat-pass-detail "35 đạt · 1 không đạt" — its last line sits -101px above the rule on top of article.stat:nth-of-type(2)
- **flush** (390): div#overview > div.stats-grid > article.stat:nth-of-type(3) > div.stat-foot "Điểm phần trăm · macro theo tác vụ" — its last line sits -100px above the rule on top of article.stat:nth-of-type(4)
- **no-visual** (390): div#overview > div.analysis-grid > section.panel.config-panel "Cấu hình đánh giá" — no picture, effect or mock in this section; a feature section needs a visual
- **no-visual** (390): div#overview > section.panel.results-panel "Chi tiết lượt chạy" — no picture, effect or mock in this section; a feature section needs a visual
- **button-styles** (390): (the page) — 3 button styles on the page: soft, fill #eaf2ec x1 ("▦ Tổng quan"); soft, fill #174b3b, outline #174b3b x1 ("＋ Chạy benchmark"); soft, outline #dce2dd x2 ("↓ Tải CSV")
- **container** (1440, 390): page — no .wrap

## Warnings

- **copy-buttons**: "▦ Tổng quan" does not start with a verb (book, buy, try, start, get, see...) (and 2 more like it: "↓ Tải CSV", "↓ JSON")
- **copy-actions**: the main action "Chạy smoke" does not read word for word the same in the nav or hero and the closing section
- **off-grid**: the section's heading starts at 1032px, 770px off the page margin (262px), and no other section starts there
- **stranded-action**: stands 710px across from the nearest text of its block ("Bộ tác vụ tiếng Việt")
- **copy-length**: 1 section over 90 words a screen outside the UI mocks ("Chi tiết lượt chạy" 185); 41 words a screen across the page (326 words in 8 screens): a tech page says it in about 80 or fewer
- **skip-link**: the first Tab stop is "Đến nội dung", not a skip link: a keyboard user tabs through the whole nav on every visit
- **share-meta**: the head lacks og:title, og:description, og:image, twitter:card: a shared link shows no picture or title of its own
- **flush**: its first line sits 16px under the top edge of article.stat:nth-of-type(1), where the ground changes
- **flush**: its last line sits 19px above the lower edge of article.stat:nth-of-type(2), where the ground changes to article.stat:nth-of-type(3)
- **flush**: its first line sits 16px under the top edge of article.stat:nth-of-type(3), where the ground changes
- **flush**: its last line sits 18px above the lower edge of article.stat:nth-of-type(4), where the ground changes to section.panel.chart-panel
- **flush**: its last line sits 15px above the lower edge of section.panel.chart-panel, where the ground changes to section.panel.config-panel
- **flush**: its last line sits 16px above the lower edge of section.panel.config-panel, where the ground changes to section.panel.results-panel
- **flush**: its last line sits 17px above the lower edge of section.panel.results-panel, where the ground changes to the footer
- **tap-size**: a 127x33px tap target: under the 44px a phone needs
- **tap-size**: a 277x40px tap target: under the 44px a phone needs
- **card-visual**: 4 cards hold only text: no picture, icon, UI fragment or effect in any of them
- **section-gaps**: 26px between these sections, -42% against the median 45px
- **section-gaps**: 32px between these sections, -29% against the median 45px
- **section-gaps**: the sections overlap by 85px
- **section-gaps**: the sections overlap by 84px
- **button-contrast**: the button "▦ Tổng quan" (#eaf2ec) stands only 1.14:1 off the ground around it: it reads as part of the ground, or as switched off
- **copy-stat-strip**: stat strip x1
