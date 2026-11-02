# Local approximately remembered quotations — issue 145

The existing isolated SWORD-to-SQLite search pipeline is retained. Strict
all-term matches remain first; their label does not claim a verbatim quotation.
Up to 20 strong close matches follow only when there are few strict results.
Candidate retrieval is bounded to 256 rows and ranking uses content-word overlap
and the shortest matching source window. Common French/English words affect only
fallback ranking, not strict query semantics. Negations are retained and checked
within that window. Explicit quoted searches remain strict without fallback.
No AI, network text search, new dependency/index framework or subset-query
explosion is involved. Existing translation/scope filters and paging apply to
both groups, and source text is never rewritten.

The existing maintained ISO aliases now recognize `fra`/`fre`/`eng` and regional
variants for supported normalization. The derived search-cache signature changes
from 4 to 5 only when alias normalization changes the stored accent behavior.
Compatible English/French caches remain usable without rebuilding; resource files,
preferences, notes and sessions are not migrated/reset. Greek accents and
unsegmented-language semantics are not broadened into unsupported approximation.

Actual downloaded YouVersion edition 21 (Semeur 2015): the reported unquoted
query returned no result before and now returns John 3:16 as its sole close
match. Its quoted form still returns none. The strict query “Dieu tant aimé
monde” returns that verse normally. A local first index/query took about 2.93 s;
warm source queries were around 0.23–0.27 s, including subprocess startup.
These are local source measurements, not installed Flatpak/client-desktop timing;
the final receipt records the exact candidate and native UI latency. Do not
compare a cold cache build directly against a warm previous-version lookup.

Synthetic prose checks cover strict-before-close ordering, paging/scope, explicit
quotes, negations, remote/common-word overlap, accents and candidate/result
bounds. Source-offset highlighting retains actual matching words. Existing
worker generation/epoch guards discard superseded results; a delayed unchanged
SearchEntry notification no longer erases an explicit submitted query.

The issue remains open. Signed candidate/update checks are still required and
numbered release 87 remains paused.
