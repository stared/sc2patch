# Missing Balance Patches - Action Required

These patches have balance changes but are NOT in our visualization (35 current patches).

## Found - Need to Download & Parse

### From Blizzard News:

1. **5.0.10** (2022-07-20)
   - URL: https://news.blizzard.com/en-us/starcraft2/23826546/starcraft-ii-5-0-10-patch-notes
   - Status: ✅ URL confirmed - 14 units + 10 buildings changed

2. **4.8.3** (2019-03-25)
   - URL: https://news.blizzard.com/en-us/starcraft2/22883350/starcraft-ii-4-8-3-patch-notes
   - Status: ⚠️ Check if has balance changes (search says bug fixes only)

3. **3.9.1** (2016-12-20)
   - URL: https://news.blizzard.com/en-us/starcraft2/20407949/starcraft-ii-legacy-of-the-void-3-9-1-patch-notes
   - Status: ✅ URL confirmed - needs parsing

### From Liquipedia (Balance Updates):

4. **5.0.2 BU** (2020-08-20)
   - URL: https://liquipedia.net/starcraft2/Patch_5.0.2
   - Changes: Baneling, Oracle, Void Ray, Tempest
   - Status: ✅ Confirmed has balance changes

5. **4.11.4 BU** (2020-03-10)
   - URL: https://news.blizzard.com/en-us/starcraft2/23312740/starcraft-ii-4-11-4-patch-notes
   - Status: ⚠️ Co-op only (not multiplayer balance)

6. **4.10.1 BU** (2019-08-21)
   - URL: https://liquipedia.net/starcraft2/Patch_4.10.1
   - Changes: Stimpack, Ghost EMP, Overlord, Infested Terran, Warp Prism, Carrier, Nexus
   - Status: ✅ Confirmed has balance changes

7. **3.3.2 BU** (2016-07-06)
   - URL: https://liquipedia.net/starcraft2/Patch_3.3.2
   - Status: ✅ Confirmed has balance changes

8. **3.3.0 BU** (2016-05-23)
   - URL: https://liquipedia.net/starcraft2/Patch_3.3.0
   - Status: ✅ Confirmed has balance changes

9. **3.1.1 BU** (2016-01-29)
   - URL: https://liquipedia.net/starcraft2/Patch_3.1.1
   - Status: ⚠️ Need to verify

## Summary

- **6-7 confirmed balance patches** need to be added
- **2-3 need verification** (Co-op vs Multiplayer)
- Most are Balance Updates (BU) that may not have dedicated Blizzard news articles
- Can scrape from Liquipedia if Blizzard URLs don't exist

## Next Steps

1. Add URLs to `data/patch_urls.json` for the confirmed ones
2. Verify 4.11.4 and 4.8.3 have multiplayer balance changes
3. Download and parse with GPT-5
4. Should reach ~42 patches total (35 current + 7 new)
