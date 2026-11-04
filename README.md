# Independently maintained study resources

The catalogue pins each immutable resource by size, SHA-256, compatible format
and actual generation date. Index updates and reviewed FR/EN vocabulary updates
are independent. These files contain relationships, source topic identifiers,
scores and reviewed names/synonyms; no Scripture quotations are bundled.

Cross-references: https://www.openbible.info/labs/cross-references/
Topics: https://www.openbible.info/topics/
Index attribution: OpenBible.info and its contributors, CC BY 4.0:
https://creativecommons.org/licenses/by/4.0/
Project vocabulary labels/synonyms: GPL-2.0-only; preferred source is the JSON
file in this branch. Original vocabulary source and authorship history:
https://github.com/icfmp/Bible/blob/e22dd2c605a6028e2329238034e92b14038734ce/bible/topic_vocabulary.py
The project history is preserved; the labels are not reattributed.

Maintain names/synonyms by reviewing `topic-vocabulary.json` in this data branch
and bumping its revision. Run the study-resource workflow in vocabulary-only
mode to deliver those changes without rebuilding the index or application.
Source identifiers join exactly; unmatched names are omitted from suggestions,
new source topics remain outside the curated list until reviewed, and missing
French names use the supplied English label. No automatic AI translation occurs.
A compatible source index missing a reviewed name remains installable.

The publisher validates complete compatible archives before archiving them,
never overwrites existing assets/tags, and updates this branch only after asset
verification. Failed validation retains prior published/installed resources.
Compatible applications refresh this small catalogue in Library > Study tools.
Offline applications keep their installed index/vocabulary and known catalogue.
