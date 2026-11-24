---
name: complete-list-collection
description: Collects the first N unique items from a paginated web listing (jobs, products, search results) into items.jsonl, with a report.md that names any problem and where to resume. Use when the user asks to collect, scrape or paginate a listing, wants the first N results, gives a listing URL, or asks to resume a crawl. Do NOT use for a single page, crawling or mapping a whole site, price monitoring, or pages that are not lists.
---

# Complete List Collection

## Inputs

- The listing URL, the target N, and the sort order. Take them from the user's request; if the sort order is not given, record the one the listing shows on page 1.
- Before fetching page 1, state the URL, N, the sort order and the stable ID you will use (see Rules).
- Write items.jsonl and report.md to the current working directory.
- Fetch over plain HTTP: `curl -sS --fail --max-time 15 "<page-url>"`, or the same request with WebFetch or Python requests if there is no shell. A non-zero exit, an HTTP error or a timeout is a failed fetch. Use a browser (Playwright) only when page 1 shows no items without JavaScript.

## Rules

- MUST append each page's new items to items.jsonl BEFORE fetching the next page, because a failed fetch must not lose what was already confirmed.
- MUST identify items by a stable ID: the item's own ID if the page shows one, otherwise its URL without tracking parameters. Never by title, because titles repeat across distinct items.
- Never invent, guess or pad items to reach N, because a padded list looks complete and is wrong. Report the confirmed count as it is.
- MUST stop at N confirmed items, or at the first stop condition below, and fetch nothing after it, because every extra fetch can hit a shift or a failure that is not part of this run.
- MUST write report.md for every run, finished or stopped.

## Each page, in this order

Copy this checklist and track progress:

```
- [ ] Inputs stated: URL, N, sort order, stable ID
- [ ] Each page: fetch, read items, check sort, sort out repeats, save, decide
- [ ] report.md written and the final check passed
```

Page size is the number of items page 1 shows. Go to the next page by the listing's own "next" link; use a page parameter only when there is none.

1. **Fetch.** On an HTTP error, a timeout or a page that cannot be parsed, fetch it once more. Two failures in a row: stop with `page-failed`.
2. **Read the items.** For each: id, title, url, page, position (1-based on the page). A page with no items: stop with `ended-early`.
3. **Check the sort.** If the sort label or order differs from the one recorded, stop with `sort-changed` and save nothing from this page: its items are from another list.
4. **Sort out repeats.** An item whose ID is already in items.jsonl is a repeat: skip it and add 1 to duplicates removed. If the repeats are this page's first items and match the previous page's last items in the same order, an item was inserted above them while you crawled: record `items-shifted` on this page and go on. Repeats anywhere else are plain duplicates, not a problem.
5. **Save.** Append the new items to items.jsonl in page order, one JSON object per line, until the confirmed count reaches N. The file on disk must hold them before the next fetch: a script you write appends inside the page loop, never collects items in memory to write once at the end:

   ```python
   with open("items.jsonl", "a", encoding="utf-8") as f:  # once per page, before the next fetch
       for item in new_items:
           f.write(json.dumps(item, ensure_ascii=False) + "\n")
   ```
6. **Decide.** N reached: stop, done. The page had fewer items than the page size: the listing has ended; if the count is below N, stop with `ended-early`. Otherwise fetch the next page.

A removal above the crawl point moves items up, and one is skipped without any sign in the IDs. If the listing shows item numbers or a total count, compare them with what you saved, and record `items-shifted` if they disagree.

## Resume point

The page to fetch next and the last ID saved:

- Stopped at N in the middle of a page: that same page, because its remaining items were not saved.
- Stopped after a whole page was saved: the next page.
- `page-failed` or `sort-changed`: the page that failed or changed.

To resume, read report.md for the page, load every ID in items.jsonl, record the sort again, and start at that page, skipping every ID already saved (not only the ones before the last ID: items may have moved since).

## Output format

items.jsonl, one object per line:

```json
{"id": "item-123", "title": "Baker", "url": "https://example.com/items/item-123", "page": 1, "position": 3}
```

report.md, with every line filled:

````markdown
# Collection report

- Requested N: <number>
- Confirmed count: <number>
- Duplicates removed: <number>
- Problems detected: <none, or each as "<name> on page <p> (<what you saw>)", separated by "; ">
- Resume point: page <p>, after ID <id>
````

Problem names: `page-failed`, `ended-early`, `sort-changed`, `items-shifted`. In the parentheses say what you saw, so a reader can act on it without the crawl log: `sort-changed on page 4 (posted_desc → relevance)`, `page-failed on page 5 (HTTP 500 twice in a row)`, `items-shifted on page 2 (item-10 repeated at the top)`.

Before you finish, check: items.jsonl has no repeated ID and every line has id, title, url, page and position; the confirmed count in report.md equals the number of lines; if the count is below N, Problems detected names why.

## Examples

Listings with 10 items per page, IDs item-1, item-2, …

- N=15, nothing wrong. Page 1 gives item-1 to item-10, page 2 item-11 to item-20; saving stops at item-15. → Confirmed 15, duplicates 0, problems none, resume page 2 after item-15.
- N=25, page 2 repeats item-3 and item-7 in the middle. → Confirmed 25 (item-1 to item-25, the last on page 3), duplicates 2, problems none, resume page 3 after item-25.
- N=25, a new item is inserted at the top during the crawl, so page 2 starts with item-10 again. → Duplicates 1, problems `items-shifted on page 2 (item-10 repeated at the top)`, confirmed 25, resume page 3 after item-25.
- N=40, the sort label changes from "Newest" to "Relevance" on page 4. → Confirmed 30, problems `sort-changed on page 4 (Newest → Relevance)`, nothing saved from page 4, resume page 4 after item-30.
- N=100, the listing has 50 items; page 5 is full, page 6 is empty. → Confirmed 50, problems `ended-early on page 6 (no items)`, resume page 6 after item-50.
- N=45, page 5 fails twice. → Confirmed 40, problems `page-failed on page 5 (HTTP 500 twice in a row)`, resume page 5 after item-40.
