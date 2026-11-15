SUMMARY: The registry names Greg Schardt as the registered owner, and the account Mr. Evil has the only logon count above 0, which is 15. Uninstall records name Cain & Abel, Look@LAN, Network Stumbler, Ethereal, WinPcap, 123 Write All Stored Passwords and Anonymizer Bar. On 2004-08-27, after a logon for Mr. Evil at 15:08:23 UTC, prefetch times show NETSTUMBLER.EXE at 15:12:35 UTC and ETHEREAL.EXE at 15:34:54 UTC. The file interception in the Mr. Evil profile holds HTTP requests to mobile.msn.com and Passport hosts from a client with a Windows CE User-Agent. The files lalsetup250.exe, netstumblerinstaller_0_4_0.exe, WinPcap_3_01_a.exe and ethereal-setup-0.10.6.exe went to the Recycle Bin, but the file system does not mark them deleted. I infer, with moderate confidence, that the person who used the account Mr. Evil set up wireless capture tools and used the name Greg Schardt.

**Two things to know first**
- **No answers could be saved to the answer store.** Every attempt to bind an answer was refused with `missing_public_claim_scope_requirement`; Q1 was also refused with `missing_public_claim_row_requirement`. The cause is the public schema, not missing evidence. The JSON at the end is the submission, and every value in it comes from a certified finding.
- **Saved work notes cover only Q1–Q4, Q10, Q15, Q20 and Q24.** Each note update returns the whole plan, which is very large, so I stopped there. The plan therefore lists 23 questions as "not started", even though they have certified findings below. No conflicts were found, and no extra evidence could be collected for this run.

**Findings by question**
- **Q1:** A013. The recomputed MD5 matches the MD5 recorded at acquisition. This does not prove the image is authentic.
- **Q2:** A003.
- **Q3:** A004. The value is stored in UTC. The local offset is not certified, so I give it with a Z offset.
- **Q4:** A005. The certified value is the name "Central Standard Time" only. The registry also stores a bias of 360 minutes (UTC−06:00) and a daylight bias of −60 minutes. Those offsets are in the record details and are not certified.
- **Q5:** A006.
- **Q6:** A007.
- **Q7:** A008.
- **Q8:** A009 and A139. The source value is 2004-08-27 15:46:33.109216Z. I give it to the whole second.
- **Q9:** A010, with the five account names in A110, A112, A114, A116 and A118.
- **Q10:** A110–A119, A011, A138 and conclusion C001. Not established: this field needs a "predominant account" claim type that does not exist. C001 infers Mr. Evil.
- **Q11:** A011 (the stored last-logon name) and A138 (a logon event for Mr. Evil).
- **Q12:** A014, A015, A143 and A145. The same file, irunin.ini, records the owner Greg Schardt, the username Mr. Evil and an administrator flag of True (A016–A019). Conclusion C004.
- **Q13:** A023 and A024.
- **Q14:** A021, A022 and A145.
- **Q15:** C002. Not established: no claim type can link a setup to a network card. Linking the MAC prefix 00:10:A4 to Xircom needs a vendor lookup outside the records.
- **Q16:** A038–A043. A044, A045 and A048 are other installed programs I did not count. A123–A130 show execution traces for some of these tools.
- **Q17:** A025, A026, A027 and A147.
- **Q18:** A028, A029 and A147. The SMTP server is smtp.sbcglobal.net (A030, A031).
- **Q19:** A046, A047, A132, A149, A150 and conclusion C005. The install record names the program "OutlookExpress", and its program file is msimn.exe.
- **Q20:** A102–A109 and conclusion C009. Not established: the records are newsgroup mailbox files, and the record type itself says subscription is not proven. No subscription record exists.
- **Q21:** A148, which ties all values to the mIRC settings file mirc.ini.
- **Q22:** A050–A060, which are 11 log files.
- **Q23:** A061 and A062. The full path is `C:\Documents and Settings\Mr. Evil\interception`.
- **Q24:** A094 and C003. Not established: the field needs a device-type interpretation that no claim type supports. A User-Agent string alone is not enough, and it can be faked.
- **Q25:** A090–A093, A095 and A096. Conclusion C003 infers that the client used MSN Hotmail.
- **Q26:** A097, A098 and A099, from the Yahoo pages ShowLetter[1].htm and login[1].htm.
- **Q27:** A100 and A101.
- **Q28:** A063, A069–A076 and C006.
- **Q29:** A065–A068 (deleted flag is False) and C006.
- **Q30:** A064 and A153–A155. All three deleted entries are files under `WINDOWS\system32\wbem\Repository\FS`.
- **Q31:** A080–A089 and C008. The scanner was ClamAV 1.5.4 and the scan is incomplete. It stopped at a 300-second time limit, and it skipped pagefile.sys, unallocated space and deleted files. It reported 6 matches.
- **Activity timeline:** A123–A142 and C007.

```json
{
 "schema_version": 2,
 "case_id": "nist-cfreds-hacking",
 "answers": [
  {"question_id":"Q1","status":"answered","answer":{"image_hash":{"algorithm":"MD5","digest":"aee4fcd9301c03b3b054623ca261959a"},"acquisition_verification_match":true}},
  {"question_id":"Q2","status":"answered","answer":{"operating_system":"Microsoft Windows XP"}},
  {"question_id":"Q3","status":"answered","answer":{"installed_at":"2004-08-19T22:48:27Z"}},
  {"question_id":"Q4","status":"answered","answer":{"time_zone_setting":"Central Standard Time"}},
  {"question_id":"Q5","status":"answered","answer":{"registered_owner":"Greg Schardt"}},
  {"question_id":"Q6","status":"answered","answer":{"computer_account_name":"N-1A9ODN6ZXK4LQ"}},
  {"question_id":"Q7","status":"answered","answer":{"primary_domain_name":"EVIL"}},
  {"question_id":"Q8","status":"answered","answer":{"shutdown_at":"2004-08-27T15:46:33Z"}},
  {"question_id":"Q9","status":"answered","answer":{"account_count":5}},
  {"question_id":"Q10","status":"unknown","answer":{}},
  {"question_id":"Q11","status":"answered","answer":{"account_name":"Mr. Evil"}},
  {"question_id":"Q12","status":"answered","answer":{"file_path":"C:\\Program Files\\Look@LAN\\irunin.ini","program":"Look@LAN"}},
  {"question_id":"Q13","status":"answered","answer":{"network_cards":["Compaq WL110 Wireless LAN PC Card","Xircom CardBus Ethernet 100 + Modem 56 (Ethernet Interface)"]}},
  {"question_id":"Q14","status":"answered","answer":{"ip_address":"192.168.1.111","mac_address":"00:10:A4:93:3E:09"}},
  {"question_id":"Q15","status":"unknown","answer":{}},
  {"question_id":"Q16","status":"answered","answer":{"programs":["Cain & Abel","Ethereal","123 Write All Stored Passwords","Anonymizer Bar","Look@LAN","Network Stumbler"]}},
  {"question_id":"Q17","status":"answered","answer":{"email_address":"whoknowsme@sbcglobal.net"}},
  {"question_id":"Q18","status":"answered","answer":{"nntp_server":"news.dallas.sbcglobal.net"}},
  {"question_id":"Q19","status":"answered","answer":{"programs":["Microsoft Outlook Express","Forté Agent"]}},
  {"question_id":"Q20","status":"unknown","answer":{}},
  {"question_id":"Q21","status":"answered","answer":{"real_name":"Mini Me","email_address":"none@of.ya","nickname":"Mr","alternate_nickname":"mrevilrulez"}},
  {"question_id":"Q22","status":"answered","answer":{"channels":["#Elite.Hackers.UnderNet.log","#evilfork.EFnet.log","#ushells.UnderNet.log"]}},
  {"question_id":"Q23","status":"answered","answer":{"file_name":"interception"}},
  {"question_id":"Q24","status":"unknown","answer":{}},
  {"question_id":"Q25","status":"answered","answer":{"websites":["mobile.msn.com","login.passport.net","login.passport.com","www.passportimages.com"]}},
  {"question_id":"Q26","status":"answered","answer":{"email_address":"mrevilrulez@yahoo.com"}},
  {"question_id":"Q27","status":"answered","answer":{"file_name":"ShowLetter[1].htm"}},
  {"question_id":"Q28","status":"answered","answer":{"executable_file_count":4}},
  {"question_id":"Q29","status":"answered","answer":{"deleted_from_file_system":false}},
  {"question_id":"Q30","status":"answered","answer":{"deleted_file_count":3}},
  {"question_id":"Q31","status":"answered","answer":{"viruses_found":true}}
 ],
 "appendices": {
  "binding_limitation": "answer() refused all bindings: missing_public_claim_scope_requirement (Q1 also missing_public_claim_row_requirement). Values above are copied from certified findings.",
  "Q1": "Logical MD5 record 8022 and acquisition MD5 record 6397 are equal (A013). Logical SHA1 da2fe30fe21711edf42310873af475859a68f300 and SHA256 65e2002fed0b286f49541c7e97dcec0dda913d51a063ceeed86782bdacda2312 are recorded but not certified.",
  "Q3_Q8": "Source values are in UTC: InstallDate 2004-08-19T22:48:27Z; ShutdownTime 2004-08-27 15:46:33.109216Z, given here to the whole second. No local offset is certified.",
  "Q4": "TimeZoneInformation StandardName; Bias 360 minutes (UTC-06:00), DaylightBias -60 minutes. The offsets are not certified.",
  "Q10": "C001: Mr. Evil logon count 15; the other 4 accounts 0. The field needs a claim type that does not exist.",
  "Q15": "C002: inferred Xircom from vendor prefix 00:10:A4. External lookup; no setup-interface claim type exists.",
  "Q16": "Certified names with versions: Cain & Abel v2.5 beta45; Ethereal 0.10.6; Look@LAN 2.50 Build 29; Network Stumbler 0.4.0 (remove only); Anonymizer Bar 2.0 (remove only); 123 Write All Stored Passwords. Times are uninstall-key last-write times.",
  "Q19": "Install records: OutlookExpress (key name) and Forté Agent. Settings sources: ntuser.dat Internet Account Manager Accounts 00000001/00000002, and C:\\Program Files\\Agent\\Data\\AGENT.INI.",
  "Q20": "Outlook Express mailbox files (not subscription records): alt.2600, alt.2600.cardz, alt.2600.codez, alt.2600.crackz, alt.2600.hackerz, alt.2600.moderated, alt.hacking, alt.dss.hack, and 15 more.",
  "Q22": "11 logs in C:\\Program Files\\mIRC\\logs; channel names are recorded separately (for example #Elite.Hackers, #evilfork, #ushells).",
  "Q24": "C003: User-Agent 'Mozilla/4.0 (compatible; MSIE 4.01; Windows CE; PPC; 240x320)' suggests a Windows CE Pocket PC handheld. It can be faked.",
  "Q25": "Path C:\\Documents and Settings\\Mr. Evil\\interception; Hotmail URLs such as /hm/folder.aspx.",
  "Q29_Q30": "INFO2 records 1-4: deleted flag False. Files deleted per the MFT: OBJECTS.MAP, INDEX.MAP, ROLL_FORWARD in WINDOWS\\system32\\wbem\\Repository\\FS.",
  "Q31": "ClamAV 1.5.4 (main/daily/bytecode .cvd), result incomplete (exit 124, 300-second time limit); allocated files only; pagefile.sys skipped. 6 matches: Abel.dll, Chrono.dl_, enum.tar.gz, superscan.exe, SECHOLE.EXE, unix_hack.tgz."
 }
}
```
