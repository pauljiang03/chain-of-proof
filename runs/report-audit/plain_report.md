I've finished going through the records. Here is the report.

---

# Findings: Iaman Informant data-leak case

All times are UTC. Local New York time (EDT) is UTC−4. Record IDs are in brackets.

**Q1. External storage attached to the PC**

F1: RM#1, the company-issued SanDisk Cruzer Fit (serial 4C530012450531101593, which is on the authorized list), was first connected to the PC on 2015-03-23 at 18:31:10 (14:31 EDT). [1, 314]
F2: At 18:31:12 the PC recorded RM#1's volume as "Authorized USB", serial 5C754D3E, and the same serial is in RM#1's own boot record. [364, 374]
F3: RM#1's USB registry key was last written on 2015-03-24 at 13:38:00, which fits RM#1 being plugged in again that morning but does not prove it. [2]
F4: RM#2, a personal SanDisk Cruzer Fit (serial 4C530012550531106501, which is not on the authorized list), was first connected to the PC on 2015-03-24 at 13:58:32 (09:58 EDT). [3, 4, 315]
F5: Two seconds later, at 13:58:34, the PC recorded a volume labelled "IAMAN $_@" with serial 9E6A5B82, which was RM#2's volume at that time. [366]
F6: At 21:02:34 on 2015-03-24 the PC recorded a volume with the same label "IAMAN $_@" but a new serial, B4D85399, which is the serial on the seized RM#2. [371, 375]
F7: A file-system entry (desktop.ini) was created on RM#2 at 19:51:47 on 2015-03-24, so RM#2 was attached to a computer again that evening, most likely this PC. [126]
F8: Optical discs labelled "IAMAN CD" were read in the PC's D: drive on 2015-03-24 with three different volume serials: E297F1A5 at 20:44:13, A58AD72A at 20:47:30 and AE88F176 at 21:01:10. [368, 369, 370]

**Q2. Web searches (the ones that matter to the case)**

F9: On 2015-03-23 between 18:02:09 and 18:06:27, the informant account searched in Chrome for "data leakage methods", "leaking confidential information", "information leakage cases", "intellectual property theft" and "how to leak a secret". [217–228]
F10: Between 18:08:31 and 18:14:11 that day, it searched in Internet Explorer for "DLP DRM", "e-mail investigation", "Forensic Email Investigation", "investigation on windows machine", "windows event logs" and "external device and forensics". [236–246]
F11: At 18:13:20 and 18:13:37 it searched for "cd burning method" and "cd burning method in windows". [243, 244]
F12: Between 18:14:50 and 18:19:03 it searched in Chrome for "cloud storage", "digital forensics", "how to delete data", "anti-forensics", "system cleaner", "how to recover data" and "data recovery tools". [247–256]
F13: At 19:55:09 and 19:56:04 on 2015-03-23 it searched for "apple icloud" and "google drive". [259, 260]
F14: Right after those searches, icloudsetup.exe (19:55:47) and googledrivesync.exe (19:56:30) were downloaded into the informant's Downloads folder. [83, 84]
F15: On 2015-03-24 at 21:06:50 it searched in Chrome for "security checkpoint cd-r". [289]
F16: On 2015-03-25 between 14:46:44 and 14:47:51 it searched in Internet Explorer for "anti-forensic tools", "eraser" and "ccleaner". [290–293]

**Q3. Files opened from each source**

F17: From RM#1, `[secret_project]_proposal.docx` (path E:\RM#1\Secret Project Data\proposal) was opened on 2015-03-23 at 18:37:20 and again in Word at 18:37:54. [21–24]
F18: From RM#1, `[secret_project]_design_concept.ppt` was opened on 2015-03-23 between 18:38:21 and 18:38:23. [26, 28, 30]
F19: From the network drive \\10.11.11.128\secured_drive, `(secret_project)_pricing_decision.xlsx` was opened on 2015-03-23 between 20:26:53 and 20:26:56. [31–35]
F20: From the same network drive, `[secret_project]_final_meeting.pptx` was opened on 2015-03-23 between 20:27:33 and 20:27:37. [36–40]
F21: From RM#2, E:\Secret Project Data\design\winter_whether_advisory.zip was opened on 2015-03-24 at 14:01:23. Its inner "ppt" folder was browsed at 14:01:29, and that folder is the internal layout of a PowerPoint .pptx file. [41, 42]
F22: From disc E297F1A5, D:\de\winter_whether_advisory.zip was opened on 2015-03-24 at 20:44:13, and its inner folders ppt, ppt\slides and ppt\slideMasters were browsed until 20:44:18. [44–48]
F23: From disc AE88F176, the sample pictures Penguins.jpg, Koala.jpg and Tulips.jpg were opened on 2015-03-24 between 21:01:10 and 21:01:14. [51–53]

**Q4. Resignation letter**

F24: `Resignation_Letter_(Iaman_Informant).docx` was created on the informant's Desktop on 2015-03-24 at 18:48:40 (14:48:40 EDT). [125]
F25: The letter was last modified on 2015-03-24 at 18:59:30 (14:59:30 EDT), with a size of 11,893 bytes. [192]
F26: The letter was opened again on 2015-03-25 at 15:28:09, and an XPS copy was created on the Desktop at 15:28:33. [55, 127]

**Q5. Copies to RM#2, deletions, e-mails, CD burning**

F27: On 2015-03-24 between 13:59:27 and 14:00:18, about one minute after RM#2 was first connected, 17 files in five sub-folders (design, pricing decision, progress, proposal, technical review) were written to RM#2 under harmless-looking names such as super_bowl.avi and diary_#1d.txt. [108–124]
F28: RM#2's `winter_whether_advisory.zip` has the same size and last-modified time as RM#1's confidential `[secret_project]_detailed_design.pptx` (16,381,123 bytes, 2014-12-16 16:10:26). [325, 340]
F29: RM#2's `winter_storm.amr` has the same size and last-modified time as RM#1's `[secret_project]_revised_points.ppt` (14,547,968 bytes, 2015-01-23 20:47:10). [327, 339]
F30: RM#2's `a_gift_from_you.gif` has the same size and last-modified time as RM#1's `[secret_project]_detailed_proposal.docx` (35,226,880 bytes, 2014-12-18 21:50:58). [330, 341]
F31: RM#2's `landscape.png` has the same size and last-modified time as RM#1's `[secret_project]_proposal.docx` (6,484,502 bytes, 2014-12-19 19:53:46). [332, 342]
F32: RM#2 was reformatted (given a new volume serial) after 19:51:48 and by 21:02:34 on 2015-03-24, and the 17 copied files were recovered only from its unallocated space. [193, 371, 375, 376]
F33: On 2015-03-24 at 19:51:47, four items named pd, prog, prop and tr were deleted from the Windows CD-burning staging folder (…\AppData\Local\Microsoft\Windows\Burn\Burn), and the Recycle Bin was later emptied. [195–198]
F34: The sizes of those four items (21,887,309; 4,526,017; 41,711,382; 5,079,142 bytes) are exactly the totals of RM#2's pricing decision, progress, proposal and technical review folders, so they were the same confidential folders staged for burning. (I calculated these totals myself from records 110–124.)
F35: On 2015-03-24 at 20:11:42, eight Windows sample pictures, an IE11 installer and a desktop.ini were also deleted from the burn staging folder. [199–208]
F36: On 2015-03-23 at 17:29:27, spy.conspirator@nist.gov e-mailed the informant "Hello, Iaman", and the informant replied at 18:44:31. [294, 295]
F37: The spy sent "Good job, buddy." at 19:14:58 and "RE: Good job, buddy." at 19:20:41 on 2015-03-23. [296, 297]
F38: The spy sent "Important request" at 19:26:22 on 2015-03-23, and the informant replied 43 seconds later at 19:27:05. [298, 299]
F39: The spy sent "RE: It's me" at 20:41:19 on 2015-03-23, and the message was later moved to Deleted Items. [300]
F40: The spy sent "Last request" on 2015-03-24 at 13:25:57, and the informant's reply at 13:35:10 was later moved to Deleted Items. [301, 302]
F41: The informant sent "RE: Watch out!" to the spy on 2015-03-24 at 19:34:02, and it was later moved to Deleted Items. [303]
F42: The informant sent "Done" to the spy on 2015-03-24 at 21:05:09, and it was later moved to Deleted Items. [304]
F43: None of the 11 recovered messages had an attachment. [294–304]
F44: Four CD-burn sessions ran on 2015-03-24, at 19:47:47, 19:56:01–19:56:11, 20:24:19–20:24:46 and 20:41:21 (15:47–16:41 EDT). Each session left burn temporary files and a CD-drive event. [305–312]

**Q6. Order of events and conclusions**

F45: The spy's first e-mail (2015-03-23 17:29:27) came before every leak-related search (from 18:02:09) and before any confidential file was opened (from 18:37:20).
F46: Within 24 minutes of the informant answering "Last request" (13:35:10 on 2015-03-24), the unauthorized RM#2 was plugged in (13:58:32) and the confidential files were copied onto it under misleading names (13:59:27–14:00:18).
F47: Conclusion (shown by the records): confidential secret-project files were moved from authorized storage onto a forbidden personal USB stick and disguised by renaming. This breaks company policy.
F48: Conclusion (inferred): confidential data was burned to CD between 19:47:47 and 20:41:21 on 2015-03-24. The confidential folders were in the burn staging area, and a disc holding the disguised design file was in the drive at 20:44:13.
F49: Conclusion (inferred): the informant tried to hide the activity. He renamed files, cleared the burn staging folder, emptied the Recycle Bin, reformatted RM#2, moved e-mails to Deleted Items and searched for anti-forensic tools. The disc of sample pictures read at 21:01 may have been a decoy.
F50: Conclusion (inferred): the data was meant to leave the company on removable media. Sending "Done" (21:05:09) and searching "security checkpoint cd-r" (21:06:50) right after the burning fits a plan to carry the CD-R through the checkpoint. No record shows the files being e-mailed or uploaded to the cloud.

**Limits**

- **The CD-R:** nothing from the CD-R (RM#3) image has been extracted, so I cannot say which of the three disc volumes, or which burn session, is the seized CD-R, or what is on it.
- **E-mail content:** message bodies were not extracted, so what "Important request", "Last request" and "Watch out!" asked for is unknown. The originals of "It's me" and "Watch out!" are not in the records.
- **File matches:** the four links between RM#1 and RM#2 files are based on size and timestamp only, not on comparing contents. Thirteen RM#2 files have no matching source record. The network drive and the rest of RM#1 were not extracted, and the copy source was not recorded.
- **Cloud services:** there are no records of iCloud or Google Drive being installed, logged into or used to upload files, so a cloud transfer is neither shown nor ruled out.
- **Timestamps:**
  - Registry key "last written" times are not connection times, and no disconnect times were extracted.
  - Times on the USB sticks were converted from New York local time.
  - The resignation letter's times come from one NTFS timestamp set only, so tampering with those times was not checked.
- **Other volumes:** CA0C7A48 and 180A0125 are the PC's own internal volumes, not external storage.
- **Older pictures on RM#2:** 23 picture files in an older layout on RM#2 were created on 2015-03-23 at about 20:55, before RM#2 was ever connected to this PC, so they were not copied from it.

