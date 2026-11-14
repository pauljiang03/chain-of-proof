The case is answered. The records show confidential files going out through the suspect's personal Google Drive on 2015-03-23, and copied in disguise to his personal USB stick and the CD-R on 2015-03-24. Every finding below was certified by the checker; anything marked C### is my own judgment from those findings, not a finding.

**Refused claims:** A009 and A010 were refused because I passed the tag name where a number was needed. I resubmitted them correctly and they were certified as A016 and A017. A091, a count over 8,321 rename records, was refused because a count can cover at most 500 records, so I dropped it. Three draft conclusions were refused for length and re-filed shorter.

**Q1 – Machine and users:** A001–A007, C002. It is a Windows 7 Ultimate SP1 machine named INFORMANT-PC, and `informant` is the main user. The accounts admin11 and temporary logged on only briefly on 2015-03-22. "Of the 334 session-event records in the evidence, none has account ITechTeam." I did not prove that admin11 or temporary never logged on later.

**Q2 – External storage:** A008, A011–A019, A021–A025, C001.
- Only two USB serials were ever connected: the authorized stick (RM#1, tagged authorized) and the personal stick (RM#2, tagged unauthorized). The disc is also tagged unauthorized.
- RM#2's current volume has no file records, but 41 entries were recovered from its unallocated space.
- C001: RM#2 was most likely reformatted on 2015-03-24. Linking its earlier volume (9E6A5B82) to this physical stick rests on the shared label and timing, which is heuristic.

**Q3 – Programs:** A026–A032. Google Drive and iCloud were installed on 2015-03-23. Eraser was installed on 2015-03-25 and ran before CCleaner ran. Excel and PowerPoint also ran on 2015-03-23, when the network-drive files were opened. Who ran each program is not recorded.

**Q4 – Web:** A033–A046, C009. The searches cover leak methods, forensic investigation, CD burning, cloud storage and anti-forensics. Late on 2015-03-24 there was "security checkpoint cd-r", and next day "eraser" and "ccleaner", each followed by the download within a minute.

**Q5 – E-mail and cloud:** A003, A047–A053, A108, C006, C007.
- The evidence holds exactly 11 e-mails between iaman and spy; four are in Deleted Items.
- The pricing-decision spreadsheet and the final-meeting slides were renamed `happy_holiday.jpg` and `do_u_wanna_build_a_snow_man.mp3`. Both were uploaded to Google Drive and deleted from it about 10 minutes later.
- **Not established:** the uploaded files' content (no hash, so the link is by name only), who downloaded them, and what the e-mails said or carried (bodies and attachments were not extracted).

**Q6 – Files:** A054–A072, C003–C005.
- Confidential files were opened from the authorized stick, from the network share `\\10.11.11.128\secured_drive`, from the personal stick's earlier volume, and from the disc.
- **Identical content is proven by hash:** four confidential files from RM#1 match `winter_whether_advisory.zip`, `winter_storm.amr`, `a_gift_from_you.gif` and `landscape.png`, recovered from RM#2 and also found on RM#3 (A062, A063).
- **Not established:** no record directly shows a copy from the PC to the stick. The other disguised files (pricing, progress, technical-review documents) are linked to their originals by name only.

**Q7 – The disc:** A014, A073–A082, C008. The disc was burned several times between 19:47 and 20:53 UTC on 2015-03-24. Its visible files are only Koala, Penguins and Tulips; the disguised confidential files survive in earlier states of the disc. Linking the three "IAMAN CD" volume serials to one disc is heuristic.

**Q8 – Covering tracks:** A024, A027, A028, A048, A050, A066–A069, A083–A090, C010, C011.
- On 2015-03-24: the CD-burn staging folders were sent to the Recycle Bin, and the personal stick was reformatted. The Google Drive deletion and the e-mails in Deleted Items are listed under Q5.
- On 2015-03-25: Eraser wiped `Desktop\temp`, CCleaner ran, and iCloud was apparently uninstalled. The uninstall is my reading of program files being moved into `C:\Config.Msi`; there is no uninstall record.
- **Not established:** what CCleaner cleaned, and what happened to the Desktop `S data` folder.

**Q9 – The story:** A092–A107, C012, open questions in C013.
1. On 2015-03-23, spy's first e-mail was followed by the leak research.
2. Confidential files were opened from the authorized stick and the network drive and collected in `Desktop\S data`.
3. Two files were renamed and uploaded to Google Drive the same day.
4. On 2015-03-24, the rest were renamed, copied to the personal stick and burned to the CD-R; the stick was then reformatted.
5. The "Done" e-mail followed, then the "security checkpoint cd-r" search.
6. On 2015-03-25, the wiping started.

My judgment (C012) is that data most likely left through Google Drive, while the stick and disc were the physical route that was stopped at the checkpoint. Still open (C013): who downloaded the Drive files, what the e-mails contained, and why RM#2 has files dated 2015-03-23, before it was first connected to this PC.
