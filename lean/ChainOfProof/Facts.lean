/-
  Facts: the evidence vocabulary. Rows are produced by the extractor, never by an LLM.

  This file is the contract between the Data and Lean roles. Changing `Kind` or `Fact`
  means changing `extractor/schema.sql` and `checker/facts.py` in the same commit.

  Meaning of `obj` / `aux` per kind (both are interned entity ids):

    kind          obj                      aux
    usbInsert     device serial            0                (USB source record; key last-write is
                                                            not exact connection onset)
    volumeMount   device serial            volume serial
    lnkTarget     retained target path     recorded target volume serial (shortcut/DestList record
                                                            timestamp; not proof of opening)
    fileCreated   file path                volume serial
    fileModified  file path                volume serial
    fileDeleted   original path            volume serial
    webSearch     query string             browser / profile
    emailSent     subject                  "from A to B", as the mailbox records them (retained
                                                            metadata and submit time, not confirmed delivery)
    cdBurn        the trace found          where it was found
    tag           tagged entity            tag id
    volumeSeen    volume label             volume serial   (the PC's registry or a shortcut recorded it)
    volumeOnDevice device serial           volume serial   (read from the seized device's image)
    unallocatedOnDevice device serial      area id         (the seized device's image has directory
                                                            entries left outside any current file;
                                                            recovered fileCreated / fileModified rows
                                                            carry the same area id in `aux`)
    systemSetting setting name             its value       (t = when the setting was written, or
                                                            the moment the setting itself records)
    accountSeen   account name or id       what it is an account of (a Windows local account,
                                                            a cloud service, an e-mail client)
    sessionEvent  logon / logoff / startup / shutdown / ...   the account, or 0 for the machine
    programInstalled program name          version          (registration/installer record; t retains
                                                            source meaning, not necessarily installation time)
    programRun    executable name          recorded path    (legacy application observation; provenance
                                                            cannot upgrade the kind to execution evidence)
    webVisit      URL                      browser
    fileDownloaded saved path              source URL
    localSearch   text typed               where it was typed
    cloudFile     file name or cloud path  "<service>: <event>"
    noteText      text of the note         application
    folderOpened  folder path              artifact that records it (shell bag, ...)
    fileRenamed   old name                 new name
    fileSeen      file path                secondary artifact that records it (search index,
                                                            thumbnail cache, shadow copy, ...)
    shadowCopy    shadow copy id           volume
    fileContent   file path                "sha256:<hex>"  (t = when the image was examined)
    fileRemoved   file path                volume serial   (t = journal record carrying FILE_DELETE;
                                                            not exact deletion onset or a wiping assertion)
    volumeRecorded physical disc id        volume serial   (t = UDF file-set descriptor recording
                                                            time, not examination or write completion)
    fileCreationRecorded file path         volume serial   (t = journal record carrying FILE_CREATE;
                                                            not a filesystem creation timestamp)
    journalName   observed name/path       scoped NTFS identity (image, full volume serial,
                                                            file record and sequence; journal observation time)
    journalParent scoped child identity    scoped parent identity (journal observation time)
    journalRemoval observed name/path      scoped NTFS identity (removal-flag observation,
                                                            not onset, every alias removed, or wiping)
    journalPath   bounded historical path  scoped NTFS identity (child journal observation time;
                                                            an incomplete ancestor is marked explicitly)
-/
namespace ChainOfProof

inductive Kind where
  | usbInsert | volumeMount | lnkTarget
  | fileCreated | fileModified | fileDeleted
  | webSearch | emailSent | cdBurn
  | tag
  | volumeSeen | volumeOnDevice
  | unallocatedOnDevice
  | systemSetting | accountSeen | sessionEvent | programInstalled | programRun
  | webVisit | fileDownloaded | localSearch | cloudFile | noteText
  | folderOpened | fileRenamed | fileSeen | shadowCopy
  | fileContent
  | fileRemoved | volumeRecorded
  | fileCreationRecorded
  | journalName | journalParent | journalRemoval
  | journalPath
  -- Source-bound typed attributes; role kinds have fixed reviewed meanings.
  | attributeSubject
  | attributeTextValue
  | attributeIntegerValue
  | attributeBooleanValue
  | roleImageLogicalMd5
  | roleImageLogicalSha1
  | roleImageLogicalSha256
  | roleImageAcquisitionMd5
  | roleImageAcquisitionSha1
  | roleOsProductName
  | roleOsInstallTime
  | roleOsTimeZoneSetting
  | roleOsRegisteredOwner
  | roleMachineAccountName
  | roleMachinePrimaryDomain
  | roleMachineLastShutdown
  | roleAccountName
  | roleAccountCount
  | roleAccountLogonCount
  | roleAccountLastLogon
  | roleAccountEnabled
  | roleAccountLastLogonName
  | roleNetworkDescription
  | roleNetworkIpAddress
  | roleNetworkMacAddress
  | roleSourcePath
  | roleAppName
  | roleAppConfigRealName
  | roleAppConfigNickname
  | roleAppConfigUsername
  | roleAppConfigEmail
  | roleAppConfigSmtpServer
  | roleAppConfigNntpServer
  | roleAppConfigNewsgroup
  | roleAppConfigIrcServer
  | roleAppConfigIrcChannel
  | roleAppConfigField
  | roleTrafficUserAgent
  | roleTrafficHttpHost
  | roleTrafficUrl
  | roleTrafficFileName
  | roleTrafficHttpMethod
  | roleBrowserEmailAddress
  | roleBrowserCacheFileName
  | roleRecycleExecutableCount
  | roleRecycleFilePresent
  | roleRecycleOriginalPath
  | roleRecycleStoredPath
  | roleFilesystemDeletedCount
  | roleFilesystemDeletedPath
  | roleFilesystemAllocated
  | roleScannerVersion
  | roleScannerResult
  | roleScannerScope
  | roleScannerSignature
  | roleAppConfigRegisteredOwner
  | roleAppConfigIsAdmin
  | roleAppConfigAlternateNickname
  | roleAppConfigHostname
  | roleScannerDetectionsFound
  | roleFilesystemDeletedFlag
  | roleBrowserUrl
  | roleAppNewsGroupMailbox
  | roleAppConfigIrcLogFileName
  | roleAppBinaryProductName
  | roleAppBinaryProductVersion
  | roleAppBinaryFileDescription
  | roleAppBinaryFileVersion
  | roleAppExecutionProgram
  | roleAppExecutionPath
  | roleOsVersion
  | roleOsBuildNumber
  | roleOsSystemRoot
  | roleAppExecutionRecordedTime
  | roleAppExecutionSourceType
  | roleAppExecutionTimeMeaning
  | roleAppExecutionRunCount
  | roleAppExecutionRawRunCount
  | roleBrowserHistoryBrowser
  | roleBrowserHistoryPath
  | roleMailStorePath
  | roleThumbcacheContainerPath
  | roleStickyNotesContainerPath
  | roleMailMessageBodyUnicode
  | roleMailMessageSubjectUnicode
  | roleDocumentContainerPath
  | roleDocumentContainerFormat
  | roleDocumentCoreTitle
  | roleDocumentCoreSubject
  | roleDocumentCoreCreator
  | roleDocumentCoreLastModifiedBy
  | roleDocumentCoreDescription
  | roleDocumentCoreKeywords
  | roleDocumentCoreCreated
  | roleDocumentCoreModified
  | roleOsEffectiveTimeZone
  | roleBrowserYahooMailCacheFileName
  | roleVssCopyId
  | roleVssSetId
  | roleVssStoragePath
  | roleVssCreatedAt
  | roleBrowserSearchUrl
  | roleBrowserSearchQuery
  | roleBrowserSearchBrowser
  | roleBrowserSearchRecordedTime
  | roleRecycleIndexFileName
  | roleRecycleIndexDeletedAt
  -- A completed declared extraction procedure and its exact source-scoped members.
  -- obj = scoped set identity; declaration aux = procedure/definition;
  -- member aux = scoped file identity. t = examination, not deletion onset.
  | filesystemSet
  | filesystemMemberDeleted
  | filesystemMemberAllocated
  | filesystemMemberUnknown
  | roleStickyNotesNoteText
  | roleStickyNotesContainerModifiedAt
  -- Canonical signed decimal source scalar. The slot remains an interned entity;
  -- this is not a timestamp, a count or a new integer arithmetic primitive.
  | attributeSignedIntegerValue
  | roleCloudContainerService
  | roleCloudContainerType
  | roleCloudContainerPath
  | roleCloudGoogleDriveDocumentId
  | roleCloudGoogleDriveFileName
  | roleCloudGoogleDriveServerModifiedAt
  | roleCloudGoogleDriveDeletionRecordServerModifiedAt
  | roleCloudGoogleDriveCredentialsAccount
  | roleCloudGoogleDriveCredentialsUsedAt
  | roleCloudGoogleDriveWorkerStage
  | roleCloudGoogleDriveWorkerDirection
  | roleCloudGoogleDriveWorkerAction
  | roleCloudGoogleDriveWorkerFileName
  | roleCloudGoogleDriveWorkerRecordedAt
  | roleDocumentOleTitle
  | roleDocumentOleSubject
  | roleDocumentOleAuthor
  | roleDocumentOleKeywords
  | roleDocumentOleComments
  | roleDocumentOleTemplate
  | roleDocumentOleLastAuthor
  | roleDocumentOleRevision
  | roleDocumentOleApplication
  | roleDocumentOleCreatedFiletime
  | roleDocumentOleLastSavedFiletime
  | roleDocumentPdfTitle
  | roleDocumentPdfAuthor
  | roleDocumentPdfSubject
  | roleDocumentPdfKeywords
  | roleDocumentPdfCreator
  | roleDocumentPdfProducer
  | roleDocumentPdfCreated
  | roleDocumentPdfModified
  | roleMailMessageSubjectString8
  | roleMailMessageBodyString8
  | roleMailMessageBodyHtml
  | roleDocumentSourcePath
  | roleDocumentSourceFormat
  | roleAccountRid
  | roleNetworkDhcpDeviceName
  | roleNetworkDhcpIpAddress
  | roleNetworkDhcpSubnetMask
  | roleNetworkDhcpNameServer
  | roleNetworkDhcpDomain
  | roleNetworkDhcpDefaultGateway
  | roleNetworkDhcpServer
  | roleNetworkDhcpEnabled
  | roleOsTimeZoneBiasMinutes
  | roleOsTimeZoneStandardBiasMinutes
  | roleOsTimeZoneDaylightBiasMinutes
  | roleOsTimeZoneActiveBiasMinutes
  | rolePartitionNumber
  | rolePartitionBootable
  | rolePartitionStartSector
  | rolePartitionTotalSectors
  | rolePartitionFilesystem
  | roleSearchConfigRegistryKey
  | roleSearchConfigValueName
  | roleSearchConfigValueText
  | roleSearchConfigValueInteger
  | roleSearchServiceRegistryKey
  | roleSearchServiceStartCode
  | roleSearchServiceStartType
  | roleSnapshotExclusionRegistryKey
  | roleSnapshotExclusionValueName
  | roleSnapshotExclusionPattern
  | roleSearchIndexContainerPath
  | roleSearchIndexTable
  | roleSearchIndexDocumentId
  | roleSearchIndexIdentifierColumn
  | roleSearchIndexItemUrl
  | roleSearchIndexItemPath
  | roleSearchIndexDateModified
  | roleSearchIndexDateCreated
  | roleSearchIndexStore
  | roleSearchIndexItemType
  | roleSearchIndexKind
  | roleEventProvider
  | roleEventChannel
  | roleEventEventId
  | roleEventRecordId
  | roleEventRecordedTime
  | roleEventDescription
  | roleEventTimeMeaning
  | roleEventAccountName
  | roleEventAccountSid
  | roleMailRecoveredSubjectUnicode
  | roleMailRecoveredBodyUnicode
  deriving DecidableEq, Repr

structure Fact where
  id   : Nat    -- row id in the evidence DB
  kind : Kind
  t    : Nat    -- UTC microseconds since the Unix epoch
  res  : Nat    -- timestamp uncertainty in µs: the true time lies within (t - res, t + res)
  obj  : Nat    -- interned primary entity
  aux  : Nat    -- interned secondary entity
  deriving Repr

/-- A stud: one of a fact's two entity slots. -/
inductive Slot where
  | obj | aux
  deriving DecidableEq, Repr

def Fact.get (f : Fact) : Slot → Nat
  | .obj => f.obj
  | .aux => f.aux

end ChainOfProof
