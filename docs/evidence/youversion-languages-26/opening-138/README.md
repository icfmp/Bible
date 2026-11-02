# Independent ordinary reading — issues 26 and 138

A real local GTK controller call reproduced the same cause as #138: Library Read raised `VersificationMismatch` when switching from a correctly installed edition with its own source index to another correctly installed edition. The primary selector duplicated the same strict-resolution gate. Conversion and native inventories were valid.

`Original` in the client report denotes the registered reference index used for YouVersion Semeur 2015, not an original-language Bible. Louis Segond 1910 keeps its exact `YouVersion93` index. No unconditional identity mapping or source relabeling is added.

Both explicit opening routes now share a targeted handler. Verified mappings keep the exact requested passage. A missing mapping opens the target's actual first indexed passage with a localized explanation; the user can then select Genesis 19:1 in that resource's own reference system. The shared resolver stays strict for comparison, study and annotation operations.

The actual Semeur/Segond local GTK proof passes Library Read, primary selector, new tab and offline session restore, including Gen 19:1, Gen 1, Psalm 119, the actual Mark 10:53 index edge and Revelation 22:21. A personal note, preferences and all eighteen installed module files stay unchanged. These local receipts do not claim installed Flatpak or client-device validation; the ordinary packaged CI now runs the same real-resource proof before allowing publication.

Issue #138 was coordinated into #26 because the failing user route also blocked the new catalogue's editions. Both issues remain OPEN. Numbered release #87 remains paused.
