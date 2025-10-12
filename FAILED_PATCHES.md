# Failed Patches - Investigation Complete ✅

## ✅ PARSER BUG FIXED AND VERIFIED!

**Root Cause:** `'general'` in `end_markers` stopped extraction at "### General" headers
**Impact:** Parser failed on patches with "### General" balance sections
**Fix:** Removed 'general' from end_markers (scripts/parse_with_llm_v2.py:60)

**Example:** 5.0.13 extraction:
- Before: 21 lines (stopped at "### General")
- After: 120 lines (includes all Terran/Zerg/Protoss/General changes)

**Verification:** Re-parsed all 13 suspected patches, recovered 2 with multiplayer balance changes

---

## ✅ RECOVERED PATCHES (2)

Parser bug fix successfully recovered these patches:

1. **3.13.0** - https://news.blizzard.com/en-gb/article/20721907/starcraft-ii-legacy-of-the-void-3-13-0-patch-notes
   - 1 entity: Queen (anti-air attack range buff)

2. **5.0.13** - https://news.blizzard.com/en-us/article/24078322/starcraft-ii-5-0-13-patch-notes
   - 19 entities with 32 total changes

**Status:** ✅ Successfully added to visualization (now showing 37 patches)

---

## ✅ CO-OP ONLY PATCHES (11) - CORRECTLY FILTERED

These patches have NO multiplayer balance changes (co-op missions or cosmetic only):

1. **2.0.8** - https://news.blizzard.com/en-us/article/9096527/starcraft-ii-patch-2-0-8-notes
2. **2.1.9** - https://news.blizzard.com/en-us/article/18446033/starcraft-ii-2-1-9-patch-notes
3. **3.4.0** - https://news.blizzard.com/en-us/article/20166144/starcraft-ii-legacy-of-the-void-3-4-0-patch-notes
4. **4.1.4** - https://news.blizzard.com/en-us/article/21313391/starcraft-4-1-4-patch-notes
5. **4.2.4** - https://news.blizzard.com/en-us/article/21700683/starcraft-ii-4-2-4-patch-notes
6. **4.3.2** - https://news.blizzard.com/en-us/article/21728663/starcraft-ii-4-3-2-patch-notes
7. **4.4.0** - https://news.blizzard.com/en-us/article/21870976/starcraft-ii-4-4-0-patch-notes
8. **4.5.0** - https://news.blizzard.com/en-us/article/22023343/starcraft-ii-4-5-0-patch-notes
9. **4.6.1** - https://news.blizzard.com/en-us/article/22492977/starcraft-ii-4-6-1-patch-notes
10. **4.7.0** - https://news.blizzard.com/en-us/article/22764996/starcraft-ii-4-7-0-patch-notes
11. **4.8.4** - https://news.blizzard.com/en-us/article/22933133/starcraft-ii-4-8-4-patch-notes

**Status:** ✅ System correctly filtered these out (GPT-5 returned no balance_changes)

---

## ⚠️ REDIRECTED URLs (3) - CANNOT DOWNLOAD

These old battle.net URLs redirect to the SC2 homepage:

1. **1.1.3** (2010-11-30) - http://us.battle.net/sc2/en/blog/1113827/patch-113-now-live-11-9-2010
2. **1.4.3 BU** (date unknown) - http://eu.battle.net/sc2/en/blog/4380324/Balance_Update_-_110512-10_05_2012
3. **2.0.9** (date unknown) - http://us.battle.net/sc2/en/blog/10278173

**Status:** Need web archive sources

---

## ✅ NO MULTIPLAYER BALANCE (Confirmed via web search)

These patches were confirmed to have NO multiplayer balance changes:

1. **4.2.2** (2018-03-27) - Nation Wars V promo items only
2. **4.10.4** (2019-10-22) - Bug fixes + INcontroL tribute bundle only

**Status:** ✅ System correctly filtered these out

---

## Summary

**Parser Investigation: COMPLETE ✅**

- **2 patches recovered** by fixing parser bug (3.13.0, 5.0.13)
- **11 co-op only** - correctly filtered out
- **2 no balance** - correctly filtered out (4.2.2, 4.10.4)
- **3 redirected** - need web archive
- **37 patches successful** - currently in visualization (was 35, +2 recovered)

**Next Steps:**
1. Find web archive sources for 3 redirected URLs
2. Add 6-7 missing balance patches from MISSING_PATCHES.md
3. Target: ~44 patches (37 current + 3 redirects + 4 missing confirmed)
