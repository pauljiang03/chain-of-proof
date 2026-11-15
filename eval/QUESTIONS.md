# The 60 public test questions

These are the prompts from the NIST CFReDS Data Leakage test. This file contains no answers.
See [the public answer contract](benchmark_nist_questions.json) for the required fields and matching rules.
Some questions request a list with many records. Each record can contain several fields.

## Q1–Q12: Images, computer settings and activity

**Q1.** What are the hash values (MD5 & SHA-1) of all images? Does the acquisition and verification hash value match?

**Q2.** Identify the partition information of PC image.

**Q3.** Explain installed OS information in detail. (OS name, install date, registered owner…)

**Q4.** What is the timezone setting?

**Q5.** What is the computer name?

**Q6.** List all accounts in OS except the system accounts: Administrator, Guest, systemprofile, LocalService, NetworkService. (Account name, login count, last logon date…)

**Q7.** Who was the last user to logon into PC?

**Q8.** When was the last recorded shutdown date/time?

**Q9.** Explain the information of network interface(s) with an IP address assigned by DHCP.

**Q10.** What applications were installed by the suspect after installing OS?

**Q11.** List application execution logs. (Executable path, execution time, execution count...)

**Q12.** List all traces about the system on/off and the user logon/logoff. (It should be considered only during a time range between 09:00 and 18:00 in the timezone from Question 4.)

## Q13–Q17: Web browsers and searches

**Q13.** What web browsers were used?

**Q14.** Identify directory/file paths related to the web browser history.

**Q15.** What websites were the suspect accessing? (Timestamp, URL...)

**Q16.** List all search keywords using web browsers. (Timestamp, URL, keyword...)

**Q17.** List all user keywords at the search bar in Windows Explorer. (Timestamp, Keyword)

## Q18–Q21: Email

**Q18.** What application was used for e-mail communication?

**Q19.** Where is the e-mail file located?

**Q20.** What was the e-mail account used by the suspect?

**Q21.** List all e-mails of the suspect. If possible, identify deleted e-mails. (You can identify the following items: Timestamp, From, To, Subject, Body, and Attachment) [Hint: just examine the OST file only.]

## Q22–Q28: USB devices and network drives

**Q22.** List external storage devices attached to PC.

**Q23.** Identify all traces related to ‘renaming’ of files in Windows Desktop. (It should be considered only during a date range between 2015-03-23 and 2015-03-24.) [Hint: the parent directories of renamed files were deleted and their MFT entries were also overwritten. Therefore, you may not be able to find their full paths.]

**Q24.** What is the IP address of company’s shared network drive?

**Q25.** List all directories that were traversed in ‘RM#2’.

**Q26.** List all files that were opened in ‘RM#2’.

**Q27.** List all directories that were traversed in the company’s network drive.

**Q28.** List all files that were opened in the company’s network drive.

## Q29–Q31: Google Drive

**Q29.** Find traces related to cloud services on PC. (Service name, log files...)

**Q30.** What files were deleted from Google Drive? Find the filename and modified timestamp of the file. [Hint: Find a transaction log file of Google Drive.]

**Q31.** Identify account information for synchronizing Google Drive.

## Q32–Q37: CD burning and the resignation document

**Q32.** What a method (or software) was used for burning CD-R?

**Q33.** When did the suspect burn CD-R? [Hint: It may be one or more times.]

**Q34.** What files were copied from PC to CD-R? [Hint: Just use PC image only. You can examine transaction logs of the file system for this task.]

**Q35.** What files were opened from CD-R?

**Q36.** Identify all timestamps related to a resignation file in Windows Desktop. [Hint: the resignation file is a DOCX file in NTFS file system.]

**Q37.** How and when did the suspect print a resignation file?

## Q38–Q46: Thumbnails, notes and Windows Search

**Q38.** Where are ‘Thumbcache’ files located?

**Q39.** Identify traces related to confidential files stored in Thumbcache. (Include ‘256’ only)

**Q40.** Where are Sticky Note files located?

**Q41.** Identify notes stored in the Sticky Note file.

**Q42.** Was the ‘Windows Search and Indexing’ function enabled? How can you identify it? If it was enabled, what is a file path of the ‘Windows Search’ index database?

**Q43.** What kinds of data were stored in Windows Search database?

**Q44.** Find traces of Internet Explorer usage stored in Windows Search database. (It should be considered only during a date range between 2015-03-22 and 2015-03-23.)

**Q45.** List the e-mail communication stored in Windows Search database. (It should be considered only during a date range between 2015-03-23 and 2015-03-24.)

**Q46.** List files and directories related to Windows Desktop stored in Windows Search database. (Windows Desktop directory: \Users\informant\Desktop\)

## Q47–Q51: Shadow copies and deleted data

**Q47.** Where are Volume Shadow Copies stored? When were they created?

**Q48.** Find traces related to Google Drive service in Volume Shadow Copy . What are the differences between the current system image (of Question 29 ~ 31) and its VSC?

**Q49.** What files were deleted from Google Drive? Find deleted records of cloud_entry table inside snapshot.db from VSC. (Just examine the SQLite database only. Let us suppose that a text based log file was wiped.) [Hint: DDL of cloud_entry table is as follows.] CREATE TABLE cloud_entry (doc_id TEXT, filename TEXT , modified INTEGER , created INTEGER , acl_role INTEGER , doc_type INTEGER, removed INTEGER , size INTEGER , checksum TEXT , shared INTEGER , resource_type TEXT, PRIMARY KEY (doc_id));

**Q50.** Why can’t we find Outlook’s e-mail data in Volume Shadow Copy?

**Q51.** Examine ‘Recycle Bin’ data in PC.

## Q52–Q57: Recovery and anti-forensics

**Q52.** What actions were performed for anti-forensics on PC at the last day ‘2015-03-25’?

**Q53.** Recover deleted files from USB drive ‘RM#2’.

**Q54.** What actions were performed for anti-forensics on USB drive ‘RM#2’? [Hint: this can be inferred from the results of Question 53.]

**Q55.** What files were copied from PC to USB drive ‘RM#2’?

**Q56.** Recover hidden files from the CD-R ‘RM#3’. How to determine proper filenames of the original files prior to renaming tasks?

**Q57.** What actions were performed for anti-forensics on CD-R ‘RM#3’?

## Q58–Q60: Incident summary

**Q58.** Create a detailed timeline of data leakage processes.

**Q59.** List and explain methodologies of data leakage performed by the suspect.

**Q60.** Create a visual diagram for a summary of results.
