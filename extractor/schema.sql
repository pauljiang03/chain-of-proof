-- Evidence DB schema (DuckDB). The contract between the extractor and the checker.
-- Mirrors lean/ChainOfProof/Facts.lean and checker/facts.py: change all three together.

CREATE TABLE IF NOT EXISTS strings (
    id BIGINT PRIMARY KEY,          -- interned id; 0 is reserved for "none"
    s  VARCHAR NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS facts (
    id   BIGINT PRIMARY KEY,
    kind VARCHAR NOT NULL CHECK (kind IN (
        'usbInsert', 'volumeMount', 'lnkTarget',
        'fileCreated', 'fileModified', 'fileDeleted',
        'webSearch', 'emailSent', 'cdBurn', 'tag',
        'volumeSeen', 'volumeOnDevice', 'unallocatedOnDevice',
        'systemSetting', 'accountSeen', 'sessionEvent', 'programInstalled', 'programRun',
        'webVisit', 'fileDownloaded', 'localSearch', 'cloudFile', 'noteText',
        'folderOpened', 'fileRenamed', 'fileSeen', 'shadowCopy', 'fileContent',
        'fileRemoved', 'volumeRecorded', 'fileCreationRecorded',
        'journalName', 'journalParent', 'journalRemoval', 'journalPath',
        'attributeSubject',
        'attributeTextValue',
        'attributeIntegerValue',
        'attributeBooleanValue',
        'roleImageLogicalMd5',
        'roleImageLogicalSha1',
        'roleImageLogicalSha256',
        'roleImageAcquisitionMd5',
        'roleImageAcquisitionSha1',
        'roleOsProductName',
        'roleOsInstallTime',
        'roleOsTimeZoneSetting',
        'roleOsRegisteredOwner',
        'roleMachineAccountName',
        'roleMachinePrimaryDomain',
        'roleMachineLastShutdown',
        'roleAccountName',
        'roleAccountCount',
        'roleAccountLogonCount',
        'roleAccountLastLogon',
        'roleAccountEnabled',
        'roleAccountLastLogonName',
        'roleNetworkDescription',
        'roleNetworkIpAddress',
        'roleNetworkMacAddress',
        'roleSourcePath',
        'roleAppName',
        'roleAppConfigRealName',
        'roleAppConfigNickname',
        'roleAppConfigUsername',
        'roleAppConfigEmail',
        'roleAppConfigSmtpServer',
        'roleAppConfigNntpServer',
        'roleAppConfigNewsgroup',
        'roleAppConfigIrcServer',
        'roleAppConfigIrcChannel',
        'roleAppConfigField',
        'roleTrafficUserAgent',
        'roleTrafficHttpHost',
        'roleTrafficUrl',
        'roleTrafficFileName',
        'roleTrafficHttpMethod',
        'roleBrowserEmailAddress',
        'roleBrowserCacheFileName',
        'roleRecycleExecutableCount',
        'roleRecycleFilePresent',
        'roleRecycleOriginalPath',
        'roleRecycleStoredPath',
        'roleFilesystemDeletedCount',
        'roleFilesystemDeletedPath',
        'roleFilesystemAllocated',
        'roleScannerVersion',
        'roleScannerResult',
        'roleScannerScope',
        'roleScannerSignature',
        'roleAppConfigRegisteredOwner',
        'roleAppConfigIsAdmin',
        'roleAppConfigAlternateNickname',
        'roleAppConfigHostname',
        'roleScannerDetectionsFound',
        'roleFilesystemDeletedFlag',
        'roleBrowserUrl',
        'roleAppNewsGroupMailbox',
        'roleAppConfigIrcLogFileName')),
    t    BIGINT NOT NULL CHECK (t   >= 0),  -- UTC microseconds since the Unix epoch
    res  BIGINT NOT NULL CHECK (res >= 1),  -- timestamp uncertainty in microseconds
    obj  BIGINT NOT NULL,                   -- strings.id; meaning per kind: see Facts.lean
    aux  BIGINT NOT NULL,                   -- strings.id
    prov VARCHAR NOT NULL                   -- JSON: image, artifact, offset, tool, source timezone
);

-- Tag facts (kind = 'tag'): obj = the tagged entity, aux = the tag's strings.id.
--   t    = when the tag was assigned (extraction time), never 0, so that no `before`
--          claim can place a tag ahead of a real event.
--   prov = {"source": "deterministic", "rule": "<what computed it>"}
--       or {"source": "llm", "model": "..."}  -> the finding is reported as a judgment.
