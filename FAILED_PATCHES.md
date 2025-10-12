# Failed Patches - Status Report

## REDIRECTED URLs (3) - CANNOT DOWNLOAD
These old battle.net URLs redirect to the SC2 homepage:

1. **1.1.3** (2010-11-30) - http://us.battle.net/sc2/en/blog/1113827/patch-113-now-live-11-9-2010
   - **Status:** URL dead/redirected

2. **1.4.3 BU** (date unknown) - http://eu.battle.net/sc2/en/blog/4380324/Balance_Update_-_110512-10_05_2012
   - **Status:** URL dead/redirected

3. **2.0.9** (date unknown) - http://us.battle.net/sc2/en/blog/10278173
   - **Status:** URL dead/redirected

**Action needed:** Find alternative sources (web archives or Liquipedia)

---

## PARSER FAILURES (15) - HTML EXISTS, EXTRACTION FAILED
These patches have balance changes but our parser failed to extract them:

### **5.0.13** (2024-03-26) - CONFIRMED HAS BALANCE CHANGES
- URL: https://news.blizzard.com/en-us/article/24078322/starcraft-ii-5-0-13-patch-notes
- **Has balance changes:** Liberator, Widow Mine, Cyclone, Raven, Infestor, Overlord, Observer, Sentry, Pylon
- **Status:** PARSER FAILURE - needs re-parsing

### Others need verification:
4. **2.0.8** - https://news.blizzard.com/en-us/article/9096527/starcraft-ii-patch-2-0-8-notes
5. **2.1.9** - https://news.blizzard.com/en-us/article/18446033/starcraft-ii-2-1-9-patch-notes
6. **3.4.0** - https://news.blizzard.com/en-us/article/20166144/starcraft-ii-legacy-of-the-void-3-4-0-patch-notes
7. **3.13.0** - https://news.blizzard.com/en-gb/article/20721907/starcraft-ii-legacy-of-the-void-3-13-0-patch-notes
8. **4.1.4** - https://news.blizzard.com/en-us/article/21313391/starcraft-4-1-4-patch-notes
9. **4.2.2** - https://news.blizzard.com/en-us/article/21647153/starcraft-4-2-2-patch-notes
10. **4.2.4** - https://news.blizzard.com/en-us/article/21700683/starcraft-ii-4-2-4-patch-notes
11. **4.3.2** - https://news.blizzard.com/en-us/article/21728663/starcraft-ii-4-3-2-patch-notes
12. **4.4.0** - https://news.blizzard.com/en-us/article/21870976/starcraft-ii-4-4-0-patch-notes
13. **4.5.0** - https://news.blizzard.com/en-us/article/22023343/starcraft-ii-4-5-0-patch-notes
14. **4.6.1** - https://news.blizzard.com/en-us/article/22492977/starcraft-ii-4-6-1-patch-notes
15. **4.7.0** - https://news.blizzard.com/en-us/article/22764996/starcraft-ii-4-7-0-patch-notes
16. **4.8.4** - https://news.blizzard.com/en-us/article/22933133/starcraft-ii-4-8-4-patch-notes
17. **4.10.4** - https://news.blizzard.com/en-us/article/23188507/starcraft-ii-4-10-4-patch-notes

**Action needed:** Fix parser or manually check if these truly have no balance changes

---

## Summary

- **3 redirected** - cannot download (need web archive)
- **15 parser failures** - downloaded but extraction failed (at least 5.0.13 confirmed has balance changes)
- **35 successful** - currently in visualization

## Next Steps

1. ✅ Visualization already shows only patches with changes (35 valid patches)
2. ⚠️ Fix parser to handle the failed patches (many likely have balance changes)
3. ⚠️ Cross-reference with Liquipedia to identify missing balance patches
4. ⚠️ Find alternative sources for 3 redirected URLs
