# Case summary: Iaman Informant data leak

The checker certified 285 findings and refused one (A134). The quoted text below is the checker's wording. My own notes only explain gaps and limits.

## 1. External storage devices attached (A001–A009)
- RM#1 (authorized): A001 and A005. A001: "USB device 4C530012450531101593 was connected to this PC (2015-03-23 18:31:10 UTC). The seized device with that serial holds volume 5C754D3E." A002 gives 2015-03-24 13:38:00 UTC, but that time is only when a registry key was last written, so it may not be a connection time. A007 ties the "Authorized USB" label to this device.
- RM#2 (personal): A003, A004 and A006. A003: "USB device 4C530012550531106501 was connected to this PC (2015-03-24 13:58:32 UTC). The seized device with that serial holds volume B4D85399." A006: "4C530012550531106501 is tagged "unauthorized-device"…". A008 ties volume B4D85399 to RM#2.
- **Limit:** A009 is only a heuristic. At first connection the PC recorded a different volume (9E6A5B82) under the same label, which suggests RM#2 was reformatted. The records cannot prove that both volumes are the same physical stick.

## 2. Web searches (A010–A094; watch-list tags A095–A117)
- All 85 search records are certified. A sample: "data leakage methods" (A018), "how to leak a secret" (A029), "cd burning method" (A044), "anti-forensics" (A051), "security checkpoint cd-r" (A090), "eraser" (A093) and "ccleaner" (A094).
- **Note:** "comapny" (A015) comes from the `admin11` account's browser history, not from `informant`.

## 3. Files opened
- **From RM#1:** A118–A127. For example: "\RM#1\Secret Project Data\proposal\[secret_project]_proposal.docx was opened (2015-03-23 18:37:20 UTC) from volume 5C754D3E, the volume on seized device 4C530012450531101593." The design_concept.ppt file was opened too (A122, A124, A126). Both files are tagged confidential (A128–A131).
- **From the network drive:** A139–A148, covering pricing_decision.xlsx and final_meeting.pptx on `\\10.11.11.128\secured_drive`. Both are tagged confidential (A149–A152).
- **From RM#2:** A132 and A133, for winter_whether_advisory.zip on volume 9E6A5B82 labelled "IAMAN $_@". A135 links that to the seized RM#2 only through the heuristic same-label step.
  - A134 was refused because the volume serial differs from the one now on the device. That direct link is not established.
- **From the CD-R:** A153–A163. These cover `\de\winter_whether_advisory.zip` at 20:44 and Penguins, Koala and Tulips .jpg at 21:01, on volumes labelled "IAMAN CD".
  - **Limit:** no records were extracted from the RM#3 image, so none of these opens can be tied to the seized CD.
  - Three different volume serials share that label (A164–A166, heuristic only).

## 4. Resignation letter (A167–A177)
- A167: "…Resignation_Letter_(Iaman_Informant).docx was created on volume CA0C7A48 (2015-03-24 18:48:40 UTC)."
- A168: "…was last modified on volume CA0C7A48 (2015-03-24 18:59:30 UTC)."
- An .xps version was created on 2015-03-25 (A174 and A175).

## 5. Copies, deletions, e-mails and CD burning
- **Copied to RM#2:** A178–A212 cover 17 directory entries recovered from RM#2's unallocated space, written between 13:59:27 and 14:00:18 UTC on 2015-03-24, after RM#2 was connected (A224). Four of them match RM#1 confidential files by size and last-modified time:
  - winter_whether_advisory.zip matches detailed_design.pptx (A213).
  - winter_storm.amr matches revised_points.ppt (A214).
  - a_gift_from_you.gif matches detailed_proposal.docx (A215).
  - landscape.png matches proposal.docx (A216).
  - **Limit:** the checker states that "contents were not compared". The other 13 entries have no matching source record. The older-layout entries were written before RM#2's first connection to this PC (A223), so they are not shown to come from this PC.
- **Deleted:** A227–A240 are 14 items in the CD-burn staging folder, sent to the Recycle Bin after the burn traces. Four e-mails sit in Deleted Items (A241–A244). RM#2's earlier file system was replaced: the recovered entries were "written before the device's current file system".
- **E-mails (A245–A255):** 11 messages between spy and iaman, from "Hello, Iaman" (2015-03-23 17:29:27 UTC) to "Done" (2015-03-24 21:05:09 UTC). The records list 0 attachments and the message bodies were not extracted.
- **CD burned:** A256–A264, all heuristic. Burn traces appear at 19:47:47, 19:56, 20:24 and 20:41:21 UTC on 2015-03-24, and the settings key changed at 20:53:16. These traces do not show what was written.

## 6. Order of events (A265–A286)
1. A spy e-mail arrives, then the leak searches start (A265).
2. RM#1 is connected and the confidential proposal is opened (A266, A267), then iaman replies (A268).
3. Confidential files are opened on the network drive (A269, A270).
4. Cloud installers are downloaded right after cloud searches (A283–A286).
5. "Last request" arrives and iaman replies, then RM#2 is connected (A271, A272).
6. Files are written to RM#2, then the zip is opened from "IAMAN $_@" (A274).
7. The resignation letter is created (A275).
8. "RE: Watch out!" is sent, then the CD is burned (A276).
9. The CD zip is opened after the last burn (A277).
10. The new RM#2 volume appears (A279).
11. "Done" is sent (A280), then iaman searches "security checkpoint cd-r" (A281) and, the next day, anti-forensics tools (A282).

**How the data left — what remains open:**
- **USB:** the strongest path is the four renamed copies on RM#2 (A213–A216). It rests on size and time matching only, not compared contents.
- **CD:** the CD path cannot be established. Nothing was extracted from the CD-R, and the burn traces do not show what was written.
- **E-mail and cloud:** there are no records of attachments or uploads.
- **Network drive:** the records cannot tie the network-drive files to any copy.
