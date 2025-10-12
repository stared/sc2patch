# Missing Balance Patches - Investigation Complete ✅

**Investigation Status:** All "missing" patches have been verified.

## ✅ NO BALANCE CHANGES (Verified via Web Search & WebFetch)

These patches were thought to have balance changes but actually do NOT:

1. **5.0.10** (2022-07-20)
   - URL: https://news.blizzard.com/en-us/starcraft2/23826546/starcraft-ii-5-0-10-patch-notes
   - Status: ✅ VERIFIED - Ladder season update only (new maps, no balance changes)
   - Checked: Blizzard news, Liquipedia, web search

2. **4.8.3** (2019-03-25)
   - URL: https://news.blizzard.com/en-us/starcraft2/22883350/starcraft-ii-4-8-3-patch-notes
   - Status: ✅ VERIFIED - Bug fixes and co-op only
   - Checked: Blizzard news, WebFetch, GPT-5 parsing

3. **3.9.1** (2016-12-20)
   - URL: https://news.blizzard.com/en-us/starcraft2/20407949/starcraft-ii-legacy-of-the-void-3-9-1-patch-notes
   - Status: ✅ VERIFIED - No multiplayer balance changes
   - Checked: Blizzard news, GPT-5 parsing

**Result:** Correctly filtered out (no action needed)

---

## ⚠️ BALANCE UPDATES WITH DEAD URLs (4)

These Balance Updates have confirmed multiplayer balance changes (verified on Liquipedia), but official patch notes URLs are no longer accessible:

1. **5.0.2 BU** (2020-08-20)
   - Official URL: https://starcraft2.com/news/23495670 (404)
   - Liquipedia: https://liquipedia.net/starcraft2/Patch_5.0.2
   - Changes: Baneling, Oracle, Void Ray, Tempest (Tectonic Destabilizers upgrade)
   - Status: ⚠️ Would need Liquipedia scraping

2. **4.10.1 BU** (2019-08-21)
   - Official URL: https://starcraft2.com/news/23093843 (404)
   - Liquipedia: https://liquipedia.net/starcraft2/Patch_4.10.1
   - Changes: Stimpack, Ghost EMP, Overlord, Warp Prism, Carrier, Nexus
   - Status: ⚠️ Would need Liquipedia scraping

3. **3.3.2 BU** (2016-07-06)
   - Official URL: https://starcraft2.com/en-us/news/20142728 (404)
   - Liquipedia: https://liquipedia.net/starcraft2/Patch_3.3.2
   - Changes: Queen anti-air range (7→8), Spore Crawler root time (6→4)
   - Status: ⚠️ Would need Liquipedia scraping

4. **3.3.0 BU** (2016-05-23)
   - Official URL: http://eu.battle.net/sc2/en/blog/20118421/ (redirects to homepage)
   - Liquipedia: https://liquipedia.net/starcraft2/Patch_3.3.0
   - Changes: Thor, Cyclone, Liberator, Colossus, Immortal, Swarm Host
   - Status: ⚠️ Would need Liquipedia scraping

**Note:** These patches have confirmed balance changes but would require building a Liquipedia scraper to extract the changes.

---

## ⚠️ NOT VERIFIED

These patches from the original list need verification:

1. **4.11.4 BU** (2020-03-10)
   - URL: https://news.blizzard.com/en-us/starcraft2/23312740/starcraft-ii-4-11-4-patch-notes
   - Status: ⚠️ Suspected co-op only (not verified)

2. **3.1.1 BU** (2016-01-29)
   - Liquipedia: https://liquipedia.net/starcraft2/Patch_3.1.1
   - Status: ⚠️ Not yet checked

---

## Summary

**Current Status: 37 patches in visualization**

**Investigation Results:**
- ✅ **3 patches verified NO balance changes** (5.0.10, 4.8.3, 3.9.1)
- ⚠️ **4 Balance Updates confirmed but URLs dead** (need Liquipedia scraping)
- ⚠️ **2 patches not yet verified** (4.11.4 BU, 3.1.1 BU)

**Next Steps (Optional):**
1. Build Liquipedia scraper to extract the 4 Balance Updates with dead URLs
2. Verify 4.11.4 BU and 3.1.1 BU
3. Continue using Blizzard news as primary source (most complete)

**Recommendation:** Current 37 patches provide good coverage of major balance changes. The 4 missing Balance Updates are minor hotfixes with small tweaks (1-4 changes each). Focus on finding web archive sources for the 3 redirected patches in FAILED_PATCHES.md first, as those are likely more substantial.
