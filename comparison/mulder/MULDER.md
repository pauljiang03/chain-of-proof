# Investigation instructions

NIST CFReDS Data Leakage: 60 public question contracts

Use only the supplied images and this public question contract.
Answer every question. Give complete requested lists and attributes.
Use unknown when the evidence does not support an answer.
Keep evidence citations in the investigation report.
Include exactly one JSON code block with the complete schema_version 2 submission.
Use the case_id and question_id values in the contract.
The JSON block must contain answers, not a self-assessed score.

## Public contract

```json
{
  "schema_version": 2,
  "case_id": "nist-cfreds-data-leakage",
  "title": "NIST CFReDS Data Leakage: 60 public question contracts",
  "time_zone": "America/New_York",
  "instructions": [
    "Answer from the supplied evidence only. Do not read benchmark_nist.json, the answer key, old references, scoring outputs or other systems' answers.",
    "Return {schema_version:2, case_id, answers:[{question_id, status, answer}]}. status is answered, unknown or unanswered.",
    "Use the listed answer schemas. Do not add explanatory keys inside answer; retain evidence references separately in your own report.",
    "All list rows are unordered. Preserve meaningful duplicates and source-specific records. Ordinal step fields carry sequence.",
    "Use UTC ISO timestamps for date-time fields. Local-minute fields use YYYY-MM-DD HH:MM in the declared timezone.",
    "Use canonical single Windows separators; omit a trailing separator for directory paths. Preserve raw unusual filename characters.",
    "Use null only for a source-reported absent/unavailable value; it is different from being unable to answer.",
    "This is a development contract. Some questions require independent reference review; systems should still attempt all 60.",
    "Questions whose reference is unresolved permit supplementary evidence-backed fields. Their schemas preserve full prompt coverage even when the private draft expected answer is incomplete. Public structural vocabularies are conventions, not extra case evidence.",
    "Every matching rule is public. JSON pointers address expected fields after unordered alignment, not required output ordering; wildcard pointer segments apply to any array member. Declared prefix matching handles source truncation, not wildcard answer filenames."
  ],
  "questions": [
    {
      "id": "Q1",
      "prompt": "What are the hash values (MD5 & SHA-1) of all images? Does the acquisition and verification hash value match?",
      "answer_schema": {
        "type": "object",
        "properties": {
          "images": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "image": {
                  "type": "string"
                },
                "md5": {
                  "type": "string"
                },
                "sha1": {
                  "type": "string"
                }
              },
              "required": [
                "image",
                "md5",
                "sha1"
              ],
              "additionalProperties": false
            }
          },
          "acquisition_verification": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "image": {
                  "type": "string"
                },
                "algorithm": {
                  "type": "string"
                },
                "acquisition_hash": {
                  "type": "string"
                },
                "verification_hash": {
                  "type": "string"
                },
                "matches": {
                  "type": "boolean"
                }
              },
              "required": [
                "image",
                "algorithm",
                "acquisition_hash",
                "verification_hash",
                "matches"
              ],
              "additionalProperties": false
            },
            "description": "Compare independently recorded acquisition and verification digests for each supplied image. The reference may be incomplete; do not omit this part of the original question."
          }
        },
        "required": [
          "images",
          "acquisition_verification"
        ],
        "additionalProperties": true,
        "description": "Reference review is unresolved. Supply the full original answer; additional evidence-backed fields are allowed and are retained for review, not automatically graded as wrong."
      },
      "match": {
        "strings": "casefold_whitespace",
        "list_order": "unordered",
        "timestamps": {}
      }
    },
    {
      "id": "Q2",
      "prompt": "Identify the partition information of PC image.",
      "answer_schema": {
        "type": "object",
        "properties": {
          "partitions": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "number": {
                  "type": "integer"
                },
                "bootable": {
                  "type": "boolean"
                },
                "filesystem": {
                  "type": "string"
                },
                "start_sector": {
                  "type": "integer"
                },
                "total_sectors": {
                  "type": "integer"
                },
                "size_as_printed": {
                  "type": "string",
                  "description": "Displayed size including unit; do not invent byte precision."
                }
              },
              "required": [
                "number",
                "bootable",
                "filesystem",
                "start_sector",
                "total_sectors",
                "size_as_printed"
              ],
              "additionalProperties": false
            }
          }
        },
        "required": [
          "partitions"
        ],
        "additionalProperties": true,
        "description": "Reference review is unresolved. Supply the full original answer; additional evidence-backed fields are allowed and are retained for review, not automatically graded as wrong."
      },
      "match": {
        "strings": "casefold_whitespace",
        "list_order": "unordered",
        "timestamps": {}
      }
    },
    {
      "id": "Q3",
      "prompt": "Explain installed OS information in detail. (OS name, install date, registered owner…)",
      "answer_schema": {
        "type": "object",
        "properties": {
          "os_name": {
            "type": "string"
          },
          "version": {
            "type": "string"
          },
          "build_number": {
            "type": "integer"
          },
          "registered_owner": {
            "type": "string"
          },
          "system_root": {
            "type": "string"
          },
          "installed_at": {
            "type": "string",
            "format": "date-time"
          }
        },
        "required": [
          "os_name",
          "version",
          "build_number",
          "registered_owner",
          "system_root",
          "installed_at"
        ],
        "additionalProperties": false
      },
      "match": {
        "strings": "casefold_whitespace",
        "list_order": "unordered",
        "timestamps": {
          "/installed_at": {
            "tolerance_seconds": 2,
            "granularity": "instant"
          }
        }
      }
    },
    {
      "id": "Q4",
      "prompt": "What is the timezone setting?",
      "answer_schema": {
        "type": "object",
        "properties": {
          "time_zone": {
            "type": "string",
            "description": "The displayed Windows timezone label, excluding the separately supplied UTC offset. Do not substitute the registry TimeZoneKeyName or an IANA identifier."
          },
          "standard_utc_offset_hours": {
            "type": "integer"
          },
          "daylight_time_bias_hours": {
            "type": "integer"
          }
        },
        "required": [
          "time_zone",
          "standard_utc_offset_hours",
          "daylight_time_bias_hours"
        ],
        "additionalProperties": false
      },
      "match": {
        "strings": "casefold_whitespace",
        "list_order": "unordered",
        "timestamps": {}
      }
    },
    {
      "id": "Q5",
      "prompt": "What is the computer name?",
      "answer_schema": {
        "type": "object",
        "properties": {
          "computer_name": {
            "type": "string"
          }
        },
        "required": [
          "computer_name"
        ],
        "additionalProperties": false
      },
      "match": {
        "strings": "casefold_whitespace",
        "list_order": "unordered",
        "timestamps": {}
      }
    },
    {
      "id": "Q6",
      "prompt": "List all accounts in OS except the system accounts: Administrator, Guest, systemprofile, LocalService, NetworkService. (Account name, login count, last logon date…)",
      "answer_schema": {
        "type": "object",
        "properties": {
          "accounts": {
            "type": "array",
            "items": {
              "anyOf": [
                {
                  "type": "object",
                  "properties": {
                    "account": {
                      "type": "string"
                    },
                    "rid_as_printed": {
                      "type": "integer"
                    },
                    "nt_hash": {
                      "type": "string"
                    },
                    "login_count": {
                      "type": "integer"
                    },
                    "created_local_as_printed": {
                      "type": "string"
                    },
                    "last_login_local_as_printed": {
                      "type": "string"
                    },
                    "login_failure_local_as_printed": {
                      "type": "string"
                    },
                    "enabled": {
                      "type": "boolean"
                    }
                  },
                  "required": [
                    "account",
                    "rid_as_printed",
                    "nt_hash",
                    "login_count",
                    "created_local_as_printed",
                    "last_login_local_as_printed",
                    "login_failure_local_as_printed",
                    "enabled"
                  ],
                  "additionalProperties": false
                },
                {
                  "type": "object",
                  "properties": {
                    "account": {
                      "type": "string"
                    },
                    "rid_as_printed": {
                      "type": "integer"
                    },
                    "nt_hash": {
                      "type": "string"
                    },
                    "login_count": {
                      "type": "integer"
                    },
                    "created_local_as_printed": {
                      "type": "string"
                    },
                    "last_login_local_as_printed": {
                      "type": [
                        "string",
                        "number",
                        "boolean",
                        "object",
                        "array",
                        "null"
                      ],
                      "description": "Use null only for a source-reported absent/unavailable value; use unknown status if the system cannot answer."
                    },
                    "login_failure_local_as_printed": {
                      "type": [
                        "string",
                        "number",
                        "boolean",
                        "object",
                        "array",
                        "null"
                      ],
                      "description": "Use null only for a source-reported absent/unavailable value; use unknown status if the system cannot answer."
                    },
                    "enabled": {
                      "type": "boolean"
                    }
                  },
                  "required": [
                    "account",
                    "rid_as_printed",
                    "nt_hash",
                    "login_count",
                    "created_local_as_printed",
                    "last_login_local_as_printed",
                    "login_failure_local_as_printed",
                    "enabled"
                  ],
                  "additionalProperties": false
                }
              ]
            }
          }
        },
        "required": [
          "accounts"
        ],
        "additionalProperties": true,
        "description": "Reference review is unresolved. Supply the full original answer; additional evidence-backed fields are allowed and are retained for review, not automatically graded as wrong."
      },
      "match": {
        "strings": "casefold_whitespace",
        "list_order": "unordered",
        "timestamps": {}
      }
    },
    {
      "id": "Q7",
      "prompt": "Who was the last user to logon into PC?",
      "answer_schema": {
        "type": "object",
        "properties": {
          "last_logged_on_user": {
            "type": "string"
          }
        },
        "required": [
          "last_logged_on_user"
        ],
        "additionalProperties": false
      },
      "match": {
        "strings": "casefold_whitespace",
        "list_order": "unordered",
        "timestamps": {}
      }
    },
    {
      "id": "Q8",
      "prompt": "When was the last recorded shutdown date/time?",
      "answer_schema": {
        "type": "object",
        "properties": {
          "last_shutdown": {
            "type": "string",
            "format": "date-time"
          }
        },
        "required": [
          "last_shutdown"
        ],
        "additionalProperties": false
      },
      "match": {
        "strings": "casefold_whitespace",
        "list_order": "unordered",
        "timestamps": {
          "/last_shutdown": {
            "tolerance_seconds": 2,
            "granularity": "instant"
          }
        }
      }
    },
    {
      "id": "Q9",
      "prompt": "Explain the information of network interface(s) with an IP address assigned by DHCP.",
      "answer_schema": {
        "type": "object",
        "properties": {
          "interfaces": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "device_name": {
                  "type": "string"
                },
                "ip_address": {
                  "type": "string"
                },
                "subnet_mask": {
                  "type": "string"
                },
                "name_server": {
                  "type": "string"
                },
                "domain": {
                  "type": "string"
                },
                "default_gateway": {
                  "type": "string"
                },
                "dhcp_enabled": {
                  "type": "boolean"
                },
                "dhcp_server": {
                  "type": "string"
                }
              },
              "required": [
                "device_name",
                "ip_address",
                "subnet_mask",
                "name_server",
                "domain",
                "default_gateway",
                "dhcp_enabled",
                "dhcp_server"
              ],
              "additionalProperties": false
            }
          }
        },
        "required": [
          "interfaces"
        ],
        "additionalProperties": false
      },
      "match": {
        "strings": "casefold_whitespace",
        "list_order": "unordered",
        "timestamps": {}
      }
    },
    {
      "id": "Q10",
      "prompt": "What applications were installed by the suspect after installing OS?",
      "answer_schema": {
        "type": "object",
        "properties": {
          "applications": {
            "type": "array",
            "items": {
              "anyOf": [
                {
                  "type": "object",
                  "properties": {
                    "installed_local_as_printed": {
                      "type": "string"
                    },
                    "name": {
                      "type": "string"
                    },
                    "version": {
                      "type": "string"
                    },
                    "manufacturer": {
                      "type": "string"
                    },
                    "installation_path": {
                      "type": "string"
                    }
                  },
                  "required": [
                    "installed_local_as_printed",
                    "name",
                    "version",
                    "manufacturer",
                    "installation_path"
                  ],
                  "additionalProperties": false
                },
                {
                  "type": "object",
                  "properties": {
                    "installed_local_as_printed": {
                      "type": "string"
                    },
                    "name": {
                      "type": "string"
                    },
                    "version": {
                      "type": "string"
                    },
                    "manufacturer": {
                      "type": "string"
                    },
                    "installation_path": {
                      "type": [
                        "string",
                        "number",
                        "boolean",
                        "object",
                        "array",
                        "null"
                      ],
                      "description": "Use null only for a source-reported absent/unavailable value; use unknown status if the system cannot answer."
                    }
                  },
                  "required": [
                    "installed_local_as_printed",
                    "name",
                    "version",
                    "manufacturer",
                    "installation_path"
                  ],
                  "additionalProperties": false
                }
              ]
            }
          }
        },
        "required": [
          "applications"
        ],
        "additionalProperties": true,
        "description": "Reference review is unresolved. Supply the full original answer; additional evidence-backed fields are allowed and are retained for review, not automatically graded as wrong."
      },
      "match": {
        "strings": "casefold_whitespace",
        "list_order": "unordered",
        "timestamps": {}
      }
    },
    {
      "id": "Q11",
      "prompt": "List application execution logs. (Executable path, execution time, execution count...)",
      "answer_schema": {
        "type": "object",
        "properties": {
          "records": {
            "type": "array",
            "items": {
              "anyOf": [
                {
                  "type": "object",
                  "properties": {
                    "timestamp": {
                      "type": "string",
                      "format": "date-time"
                    },
                    "path_or_application_id": {
                      "type": "string"
                    },
                    "execution_count": {
                      "type": [
                        "string",
                        "number",
                        "boolean",
                        "object",
                        "array",
                        "null"
                      ],
                      "description": "Use null only for a source-reported absent/unavailable value; use unknown status if the system cannot answer."
                    },
                    "source": {
                      "type": "string",
                      "enum": [
                        "Prefetch",
                        "UserAssist",
                        "Shimcache",
                        "MuiCache"
                      ]
                    },
                    "time_meaning": {
                      "type": "string",
                      "enum": [
                        "execution",
                        "file modification",
                        "unreported"
                      ]
                    }
                  },
                  "required": [
                    "timestamp",
                    "path_or_application_id",
                    "execution_count",
                    "source",
                    "time_meaning"
                  ],
                  "additionalProperties": false
                },
                {
                  "type": "object",
                  "properties": {
                    "timestamp": {
                      "type": "string",
                      "format": "date-time"
                    },
                    "path_or_application_id": {
                      "type": "string"
                    },
                    "execution_count": {
                      "type": "integer"
                    },
                    "source": {
                      "type": "string",
                      "enum": [
                        "Prefetch",
                        "UserAssist",
                        "Shimcache",
                        "MuiCache"
                      ]
                    },
                    "time_meaning": {
                      "type": "string",
                      "enum": [
                        "execution",
                        "file modification",
                        "unreported"
                      ]
                    }
                  },
                  "required": [
                    "timestamp",
                    "path_or_application_id",
                    "execution_count",
                    "source",
                    "time_meaning"
                  ],
                  "additionalProperties": false
                },
                {
                  "type": "object",
                  "properties": {
                    "timestamp": {
                      "type": [
                        "string",
                        "number",
                        "boolean",
                        "object",
                        "array",
                        "null"
                      ],
                      "description": "Use null only for a source-reported absent/unavailable value; use unknown status if the system cannot answer."
                    },
                    "path_or_application_id": {
                      "type": "string"
                    },
                    "execution_count": {
                      "type": [
                        "string",
                        "number",
                        "boolean",
                        "object",
                        "array",
                        "null"
                      ],
                      "description": "Use null only for a source-reported absent/unavailable value; use unknown status if the system cannot answer."
                    },
                    "source": {
                      "type": "string",
                      "enum": [
                        "Prefetch",
                        "UserAssist",
                        "Shimcache",
                        "MuiCache"
                      ]
                    },
                    "time_meaning": {
                      "type": "string",
                      "enum": [
                        "execution",
                        "file modification",
                        "unreported"
                      ]
                    }
                  },
                  "required": [
                    "timestamp",
                    "path_or_application_id",
                    "execution_count",
                    "source",
                    "time_meaning"
                  ],
                  "additionalProperties": false
                }
              ]
            }
          }
        },
        "required": [
          "records"
        ],
        "additionalProperties": false
      },
      "match": {
        "strings": "casefold_whitespace",
        "list_order": "unordered",
        "timestamps": {
          "/records/*/timestamp": {
            "tolerance_seconds": 2,
            "granularity": "instant"
          }
        }
      }
    },
    {
      "id": "Q12",
      "prompt": "List all traces about the system on/off and the user logon/logoff. (It should be considered only during a time range between 09:00 and 18:00 in the timezone from Question 4.)",
      "answer_schema": {
        "type": "object",
        "properties": {
          "events": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "timestamp": {
                  "type": "string",
                  "format": "date-time"
                },
                "event_id": {
                  "type": "integer"
                },
                "description": {
                  "type": "string"
                }
              },
              "required": [
                "timestamp",
                "event_id",
                "description"
              ],
              "additionalProperties": false
            }
          }
        },
        "required": [
          "events"
        ],
        "additionalProperties": false
      },
      "match": {
        "strings": "casefold_whitespace",
        "list_order": "unordered",
        "timestamps": {
          "/events/*/timestamp": {
            "tolerance_seconds": 2,
            "granularity": "instant"
          }
        }
      }
    },
    {
      "id": "Q13",
      "prompt": "What web browsers were used?",
      "answer_schema": {
        "type": "object",
        "properties": {
          "browsers": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "name": {
                  "type": "string"
                },
                "version": {
                  "type": "string"
                }
              },
              "required": [
                "name",
                "version"
              ],
              "additionalProperties": false
            }
          },
          "internet_explorer_upgraded_from_version_9_or_lower": {
            "type": "boolean"
          }
        },
        "required": [
          "browsers",
          "internet_explorer_upgraded_from_version_9_or_lower"
        ],
        "additionalProperties": false
      },
      "match": {
        "strings": "casefold_whitespace",
        "list_order": "unordered",
        "timestamps": {},
        "string_aliases": {
          "/browsers/*/name": [
            [
              "Microsoft Internet Explorer",
              "Internet Explorer",
              "IE"
            ],
            [
              "Google Chrome",
              "Chrome"
            ],
            [
              "Mozilla Firefox",
              "Firefox"
            ],
            [
              "Microsoft Edge",
              "Edge"
            ],
            [
              "Apple Safari",
              "Safari"
            ]
          ]
        }
      }
    },
    {
      "id": "Q14",
      "prompt": "Identify directory/file paths related to the web browser history.",
      "answer_schema": {
        "type": "object",
        "properties": {
          "artifacts": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "browser": {
                  "type": "string"
                },
                "path": {
                  "type": "string"
                }
              },
              "required": [
                "browser",
                "path"
              ],
              "additionalProperties": false
            }
          }
        },
        "required": [
          "artifacts"
        ],
        "additionalProperties": false
      },
      "match": {
        "strings": "casefold_whitespace",
        "list_order": "unordered",
        "timestamps": {}
      }
    },
    {
      "id": "Q15",
      "prompt": "What websites were the suspect accessing? (Timestamp, URL...)",
      "answer_schema": {
        "type": "object",
        "properties": {
          "visits": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "timestamp": {
                  "type": "string",
                  "format": "date-time"
                },
                "url": {
                  "type": "string"
                },
                "browser": {
                  "type": "string"
                }
              },
              "required": [
                "timestamp",
                "url",
                "browser"
              ],
              "additionalProperties": false
            }
          }
        },
        "required": [
          "visits"
        ],
        "additionalProperties": false
      },
      "match": {
        "strings": "casefold_whitespace",
        "list_order": "unordered",
        "timestamps": {
          "/visits/*/timestamp": {
            "tolerance_seconds": 2,
            "granularity": "instant"
          }
        },
        "string_modes": {
          "/visits/*/url": "exact",
          "/visits/4/url": "prefix",
          "/visits/15/url": "prefix"
        }
      }
    },
    {
      "id": "Q16",
      "prompt": "List all search keywords using web browsers. (Timestamp, URL, keyword...)",
      "answer_schema": {
        "type": "object",
        "properties": {
          "searches": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "timestamp": {
                  "type": "string",
                  "format": "date-time"
                },
                "keyword": {
                  "type": "string"
                },
                "url": {
                  "type": "string"
                },
                "browser": {
                  "type": "string"
                }
              },
              "required": [
                "timestamp",
                "keyword",
                "url",
                "browser"
              ],
              "additionalProperties": false
            }
          }
        },
        "required": [
          "searches"
        ],
        "additionalProperties": true,
        "description": "Reference review is unresolved. Supply the full original answer; additional evidence-backed fields are allowed and are retained for review, not automatically graded as wrong."
      },
      "match": {
        "strings": "casefold_whitespace",
        "list_order": "unordered",
        "timestamps": {
          "/searches/*/timestamp": {
            "tolerance_seconds": 2,
            "granularity": "instant"
          }
        },
        "string_modes": {
          "/searches/*/url": "exact"
        }
      }
    },
    {
      "id": "Q17",
      "prompt": "List all user keywords at the search bar in Windows Explorer. (Timestamp, Keyword)",
      "answer_schema": {
        "type": "object",
        "properties": {
          "searches": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "timestamp": {
                  "type": "string",
                  "format": "date-time"
                },
                "keyword": {
                  "type": "string"
                }
              },
              "required": [
                "timestamp",
                "keyword"
              ],
              "additionalProperties": false
            }
          }
        },
        "required": [
          "searches"
        ],
        "additionalProperties": false
      },
      "match": {
        "strings": "casefold_whitespace",
        "list_order": "unordered",
        "timestamps": {
          "/searches/*/timestamp": {
            "tolerance_seconds": 2,
            "granularity": "instant"
          }
        }
      }
    },
    {
      "id": "Q18",
      "prompt": "What application was used for e-mail communication?",
      "answer_schema": {
        "type": "object",
        "properties": {
          "application": {
            "type": "string"
          }
        },
        "required": [
          "application"
        ],
        "additionalProperties": false
      },
      "match": {
        "strings": "casefold_whitespace",
        "list_order": "unordered",
        "timestamps": {}
      }
    },
    {
      "id": "Q19",
      "prompt": "Where is the e-mail file located?",
      "answer_schema": {
        "type": "object",
        "properties": {
          "path_as_printed": {
            "type": "string"
          }
        },
        "required": [
          "path_as_printed"
        ],
        "additionalProperties": true,
        "description": "Reference review is unresolved. Supply the full original answer; additional evidence-backed fields are allowed and are retained for review, not automatically graded as wrong."
      },
      "match": {
        "strings": "casefold_whitespace",
        "list_order": "unordered",
        "timestamps": {}
      }
    },
    {
      "id": "Q20",
      "prompt": "What was the e-mail account used by the suspect?",
      "answer_schema": {
        "type": "object",
        "properties": {
          "account": {
            "type": "string"
          }
        },
        "required": [
          "account"
        ],
        "additionalProperties": false
      },
      "match": {
        "strings": "casefold_whitespace",
        "list_order": "unordered",
        "timestamps": {}
      }
    },
    {
      "id": "Q21",
      "prompt": "List all e-mails of the suspect. If possible, identify deleted e-mails. (You can identify the following items: Timestamp, From, To, Subject, Body, and Attachment) [Hint: just examine the OST file only.]",
      "answer_schema": {
        "type": "object",
        "properties": {
          "messages": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "timestamp": {
                  "type": "string",
                  "format": "date-time"
                },
                "folder_or_recovery_source": {
                  "type": "string"
                },
                "from": {
                  "type": "string"
                },
                "to": {
                  "type": "string"
                },
                "subject": {
                  "type": "string"
                },
                "body": {
                  "type": "string"
                },
                "attachments": {
                  "type": "array",
                  "items": {}
                }
              },
              "required": [
                "timestamp",
                "folder_or_recovery_source",
                "from",
                "to",
                "subject",
                "body",
                "attachments"
              ],
              "additionalProperties": false
            }
          }
        },
        "required": [
          "messages"
        ],
        "additionalProperties": false
      },
      "match": {
        "strings": "casefold_whitespace",
        "list_order": "unordered",
        "timestamps": {
          "/messages/*/timestamp": {
            "tolerance_seconds": 2,
            "granularity": "instant"
          }
        }
      }
    },
    {
      "id": "Q22",
      "prompt": "List external storage devices attached to PC.",
      "answer_schema": {
        "type": "object",
        "properties": {
          "devices": {
            "type": "array",
            "items": {
              "anyOf": [
                {
                  "type": "object",
                  "properties": {
                    "device_name": {
                      "type": "string"
                    },
                    "volume_name": {
                      "type": [
                        "string",
                        "number",
                        "boolean",
                        "object",
                        "array",
                        "null"
                      ],
                      "description": "Use null only for a source-reported absent/unavailable value; use unknown status if the system cannot answer."
                    },
                    "serial_number": {
                      "type": "string"
                    },
                    "first_connected": {
                      "type": "string",
                      "format": "date-time"
                    },
                    "connected_after_reboot": {
                      "type": "string",
                      "format": "date-time"
                    }
                  },
                  "required": [
                    "device_name",
                    "volume_name",
                    "serial_number",
                    "first_connected",
                    "connected_after_reboot"
                  ],
                  "additionalProperties": false
                },
                {
                  "type": "object",
                  "properties": {
                    "device_name": {
                      "type": "string"
                    },
                    "volume_name": {
                      "type": "string"
                    },
                    "serial_number": {
                      "type": "string"
                    },
                    "first_connected": {
                      "type": "string",
                      "format": "date-time"
                    },
                    "connected_after_reboot": {
                      "type": "string",
                      "format": "date-time"
                    }
                  },
                  "required": [
                    "device_name",
                    "volume_name",
                    "serial_number",
                    "first_connected",
                    "connected_after_reboot"
                  ],
                  "additionalProperties": false
                }
              ]
            }
          }
        },
        "required": [
          "devices"
        ],
        "additionalProperties": false
      },
      "match": {
        "strings": "casefold_whitespace",
        "list_order": "unordered",
        "timestamps": {
          "/devices/*/first_connected": {
            "tolerance_seconds": 2,
            "granularity": "instant"
          },
          "/devices/*/connected_after_reboot": {
            "tolerance_seconds": 2,
            "granularity": "instant"
          }
        }
      }
    },
    {
      "id": "Q23",
      "prompt": "Identify all traces related to ‘renaming’ of files in Windows Desktop. (It should be considered only during a date range between 2015-03-23 and 2015-03-24.) [Hint: the parent directories of renamed files were deleted and their MFT entries were also overwritten. Therefore, you may not be able to find their full paths.]",
      "answer_schema": {
        "type": "object",
        "properties": {
          "renames": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "timestamp": {
                  "type": "string",
                  "format": "date-time"
                },
                "old_name": {
                  "type": "string"
                },
                "new_name": {
                  "type": "string"
                },
                "old_usn": {
                  "type": "integer"
                },
                "new_usn": {
                  "type": "integer"
                }
              },
              "required": [
                "timestamp",
                "old_name",
                "new_name",
                "old_usn",
                "new_usn"
              ],
              "additionalProperties": false
            }
          }
        },
        "required": [
          "renames"
        ],
        "additionalProperties": false
      },
      "match": {
        "strings": "casefold_whitespace",
        "list_order": "unordered",
        "timestamps": {
          "/renames/*/timestamp": {
            "tolerance_seconds": 2,
            "granularity": "instant"
          }
        },
        "string_modes": {
          "/renames/*/old_name": "exact",
          "/renames/*/new_name": "exact"
        }
      }
    },
    {
      "id": "Q24",
      "prompt": "What is the IP address of company’s shared network drive?",
      "answer_schema": {
        "type": "object",
        "properties": {
          "ip_address": {
            "type": "string"
          }
        },
        "required": [
          "ip_address"
        ],
        "additionalProperties": false
      },
      "match": {
        "strings": "casefold_whitespace",
        "list_order": "unordered",
        "timestamps": {}
      }
    },
    {
      "id": "Q25",
      "prompt": "List all directories that were traversed in ‘RM#2’.",
      "answer_schema": {
        "type": "object",
        "properties": {
          "records": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "timestamp": {
                  "type": "string",
                  "format": "date-time"
                },
                "path": {
                  "type": "string"
                },
                "source": {
                  "type": "string",
                  "description": "Artifact vocabulary: JumpList, .LNK (Windows), .LNK (Office), Registry (Office), ShellBag (created), or ShellBag (last accessed), as supported by the specific record."
                }
              },
              "required": [
                "timestamp",
                "path",
                "source"
              ],
              "additionalProperties": false
            }
          }
        },
        "required": [
          "records"
        ],
        "additionalProperties": false
      },
      "match": {
        "strings": "casefold_whitespace",
        "list_order": "unordered",
        "timestamps": {
          "/records/*/timestamp": {
            "tolerance_seconds": 2,
            "granularity": "instant"
          }
        }
      }
    },
    {
      "id": "Q26",
      "prompt": "List all files that were opened in ‘RM#2’.",
      "answer_schema": {
        "type": "object",
        "properties": {
          "records": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "timestamp": {
                  "type": "string",
                  "format": "date-time"
                },
                "path": {
                  "type": "string"
                },
                "source": {
                  "type": "string",
                  "description": "Artifact vocabulary: JumpList, .LNK (Windows), .LNK (Office), Registry (Office), ShellBag (created), or ShellBag (last accessed), as supported by the specific record."
                }
              },
              "required": [
                "timestamp",
                "path",
                "source"
              ],
              "additionalProperties": false
            }
          }
        },
        "required": [
          "records"
        ],
        "additionalProperties": false
      },
      "match": {
        "strings": "casefold_whitespace",
        "list_order": "unordered",
        "timestamps": {
          "/records/*/timestamp": {
            "tolerance_seconds": 2,
            "granularity": "instant"
          }
        }
      }
    },
    {
      "id": "Q27",
      "prompt": "List all directories that were traversed in the company’s network drive.",
      "answer_schema": {
        "type": "object",
        "properties": {
          "records": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "timestamp": {
                  "type": "string",
                  "format": "date-time"
                },
                "path": {
                  "type": "string"
                },
                "source": {
                  "type": "string",
                  "description": "Artifact vocabulary: JumpList, .LNK (Windows), .LNK (Office), Registry (Office), ShellBag (created), or ShellBag (last accessed), as supported by the specific record."
                }
              },
              "required": [
                "timestamp",
                "path",
                "source"
              ],
              "additionalProperties": false
            }
          }
        },
        "required": [
          "records"
        ],
        "additionalProperties": false
      },
      "match": {
        "strings": "casefold_whitespace",
        "list_order": "unordered",
        "timestamps": {
          "/records/*/timestamp": {
            "tolerance_seconds": 2,
            "granularity": "instant"
          }
        }
      }
    },
    {
      "id": "Q28",
      "prompt": "List all files that were opened in the company’s network drive.",
      "answer_schema": {
        "type": "object",
        "properties": {
          "records": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "timestamp": {
                  "type": "string",
                  "format": "date-time"
                },
                "path": {
                  "type": "string"
                },
                "source": {
                  "type": "string",
                  "description": "Artifact vocabulary: JumpList, .LNK (Windows), .LNK (Office), Registry (Office), ShellBag (created), or ShellBag (last accessed), as supported by the specific record."
                }
              },
              "required": [
                "timestamp",
                "path",
                "source"
              ],
              "additionalProperties": false
            }
          }
        },
        "required": [
          "records"
        ],
        "additionalProperties": false
      },
      "match": {
        "strings": "casefold_whitespace",
        "list_order": "unordered",
        "timestamps": {
          "/records/*/timestamp": {
            "tolerance_seconds": 2,
            "granularity": "instant"
          }
        }
      }
    },
    {
      "id": "Q29",
      "prompt": "Find traces related to cloud services on PC. (Service name, log files...)",
      "answer_schema": {
        "type": "object",
        "properties": {
          "traces": {
            "type": "array",
            "items": {
              "anyOf": [
                {
                  "type": "object",
                  "properties": {
                    "service": {
                      "type": "string"
                    },
                    "type": {
                      "type": "string"
                    },
                    "path": {
                      "type": "string"
                    },
                    "deleted": {
                      "type": [
                        "string",
                        "number",
                        "boolean",
                        "object",
                        "array",
                        "null"
                      ],
                      "description": "Use null only for a source-reported absent/unavailable value; use unknown status if the system cannot answer."
                    }
                  },
                  "required": [
                    "service",
                    "type",
                    "path",
                    "deleted"
                  ],
                  "additionalProperties": false
                },
                {
                  "type": "object",
                  "properties": {
                    "service": {
                      "type": "string"
                    },
                    "type": {
                      "type": "string"
                    },
                    "path": {
                      "type": "string"
                    },
                    "deleted": {
                      "type": "boolean"
                    }
                  },
                  "required": [
                    "service",
                    "type",
                    "path",
                    "deleted"
                  ],
                  "additionalProperties": false
                }
              ]
            }
          }
        },
        "required": [
          "traces"
        ],
        "additionalProperties": true,
        "description": "Reference review is unresolved. Supply the full original answer; additional evidence-backed fields are allowed and are retained for review, not automatically graded as wrong."
      },
      "match": {
        "strings": "casefold_whitespace",
        "list_order": "unordered",
        "timestamps": {}
      }
    },
    {
      "id": "Q30",
      "prompt": "What files were deleted from Google Drive? Find the filename and modified timestamp of the file. [Hint: Find a transaction log file of Google Drive.]",
      "answer_schema": {
        "type": "object",
        "properties": {
          "files": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "filename": {
                  "type": "string"
                },
                "deleted_at": {
                  "type": "string",
                  "format": "date-time"
                },
                "modified_at": {
                  "type": "string",
                  "format": "date-time"
                }
              },
              "required": [
                "filename",
                "deleted_at",
                "modified_at"
              ],
              "additionalProperties": false
            }
          }
        },
        "required": [
          "files"
        ],
        "additionalProperties": true,
        "description": "Reference review is unresolved. Supply the full original answer; additional evidence-backed fields are allowed and are retained for review, not automatically graded as wrong."
      },
      "match": {
        "strings": "casefold_whitespace",
        "list_order": "unordered",
        "timestamps": {
          "/files/*/deleted_at": {
            "tolerance_seconds": 2,
            "granularity": "instant"
          },
          "/files/*/modified_at": {
            "tolerance_seconds": 2,
            "granularity": "instant"
          }
        }
      }
    },
    {
      "id": "Q31",
      "prompt": "Identify account information for synchronizing Google Drive.",
      "answer_schema": {
        "type": "object",
        "properties": {
          "account": {
            "type": "string"
          },
          "logon_time": {
            "type": "string",
            "format": "date-time"
          }
        },
        "required": [
          "account",
          "logon_time"
        ],
        "additionalProperties": false
      },
      "match": {
        "strings": "casefold_whitespace",
        "list_order": "unordered",
        "timestamps": {
          "/logon_time": {
            "tolerance_seconds": 2,
            "granularity": "instant"
          }
        }
      }
    },
    {
      "id": "Q32",
      "prompt": "What a method (or software) was used for burning CD-R?",
      "answer_schema": {
        "type": "object",
        "properties": {
          "method": {
            "type": "string"
          },
          "third_party_burning_application_used": {
            "type": "boolean"
          }
        },
        "required": [
          "method",
          "third_party_burning_application_used"
        ],
        "additionalProperties": false
      },
      "match": {
        "strings": "casefold_whitespace",
        "list_order": "unordered",
        "timestamps": {}
      }
    },
    {
      "id": "Q33",
      "prompt": "When did the suspect burn CD-R? [Hint: It may be one or more times.]",
      "answer_schema": {
        "type": "object",
        "properties": {
          "records": {
            "type": "array",
            "items": {
              "anyOf": [
                {
                  "type": "object",
                  "properties": {
                    "timestamp": {
                      "type": "string",
                      "format": "date-time"
                    },
                    "source": {
                      "type": "string"
                    },
                    "method": {
                      "type": "string"
                    },
                    "activity": {
                      "type": "string"
                    },
                    "temporary_files": {
                      "type": "array",
                      "items": {
                        "type": "string"
                      }
                    }
                  },
                  "required": [
                    "timestamp",
                    "source",
                    "method",
                    "activity",
                    "temporary_files"
                  ],
                  "additionalProperties": false
                },
                {
                  "type": "object",
                  "properties": {
                    "timestamp": {
                      "type": "string",
                      "format": "date-time"
                    },
                    "source": {
                      "type": "string"
                    },
                    "method": {
                      "type": "string"
                    },
                    "activity": {
                      "type": "string"
                    },
                    "temporary_files": {
                      "type": "array",
                      "items": {}
                    }
                  },
                  "required": [
                    "timestamp",
                    "source",
                    "method",
                    "activity",
                    "temporary_files"
                  ],
                  "additionalProperties": false
                }
              ]
            }
          },
          "method_selection": {
            "type": "object",
            "properties": {
              "timestamp": {
                "type": "string",
                "format": "date-time"
              },
              "source": {
                "type": "string"
              },
              "method": {
                "type": "string"
              }
            },
            "required": [
              "timestamp",
              "source",
              "method"
            ],
            "additionalProperties": false
          },
          "formatting": {
            "type": "object",
            "properties": {
              "timestamp": {
                "type": "string",
                "format": "date-time"
              },
              "source": {
                "type": "string"
              },
              "method": {
                "type": "string"
              }
            },
            "required": [
              "timestamp",
              "source",
              "method"
            ],
            "additionalProperties": false
          },
          "file_operations": {
            "type": "object",
            "properties": {
              "start": {
                "type": "string",
                "format": "date-time"
              },
              "end": {
                "type": "string",
                "format": "date-time"
              },
              "source": {
                "type": "string"
              },
              "confidential_files_created": {
                "type": "integer"
              },
              "files_renamed": {
                "type": "boolean"
              },
              "meaningless_files_created": {
                "type": "integer"
              },
              "confidential_files_deleted": {
                "type": "integer"
              }
            },
            "required": [
              "start",
              "end",
              "source",
              "confidential_files_created",
              "files_renamed",
              "meaningless_files_created",
              "confidential_files_deleted"
            ],
            "additionalProperties": false
          }
        },
        "required": [
          "records",
          "method_selection",
          "formatting",
          "file_operations"
        ],
        "additionalProperties": true,
        "description": "Reference review is unresolved. Supply the full original answer; additional evidence-backed fields are allowed and are retained for review, not automatically graded as wrong."
      },
      "match": {
        "strings": "casefold_whitespace",
        "list_order": "unordered",
        "timestamps": {
          "/records/*/timestamp": {
            "tolerance_seconds": 2,
            "granularity": "instant"
          },
          "/method_selection/timestamp": {
            "tolerance_seconds": 2,
            "granularity": "instant"
          },
          "/formatting/timestamp": {
            "tolerance_seconds": 2,
            "granularity": "instant"
          },
          "/file_operations/start": {
            "tolerance_seconds": 2,
            "granularity": "instant"
          },
          "/file_operations/end": {
            "tolerance_seconds": 2,
            "granularity": "instant"
          }
        }
      }
    },
    {
      "id": "Q34",
      "prompt": "What files were copied from PC to CD-R? [Hint: Just use PC image only. You can examine transaction logs of the file system for this task.]",
      "answer_schema": {
        "type": "object",
        "properties": {
          "paths": {
            "type": "array",
            "items": {
              "type": "string"
            }
          }
        },
        "required": [
          "paths"
        ],
        "additionalProperties": false
      },
      "match": {
        "strings": "casefold_whitespace",
        "list_order": "unordered",
        "timestamps": {}
      }
    },
    {
      "id": "Q35",
      "prompt": "What files were opened from CD-R?",
      "answer_schema": {
        "type": "object",
        "properties": {
          "records": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "timestamp": {
                  "type": "string",
                  "format": "date-time"
                },
                "path": {
                  "type": "string"
                },
                "source": {
                  "type": "string",
                  "description": "Artifact vocabulary: JumpList, .LNK (Windows), .LNK (Office), Registry (Office), ShellBag (created), or ShellBag (last accessed), as supported by the specific record."
                }
              },
              "required": [
                "timestamp",
                "path",
                "source"
              ],
              "additionalProperties": false
            }
          }
        },
        "required": [
          "records"
        ],
        "additionalProperties": false
      },
      "match": {
        "strings": "casefold_whitespace",
        "list_order": "unordered",
        "timestamps": {
          "/records/*/timestamp": {
            "tolerance_seconds": 2,
            "granularity": "instant"
          }
        }
      }
    },
    {
      "id": "Q36",
      "prompt": "Identify all timestamps related to a resignation file in Windows Desktop. [Hint: the resignation file is a DOCX file in NTFS file system.]",
      "answer_schema": {
        "type": "object",
        "properties": {
          "timestamps": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "timestamp": {
                  "type": "string",
                  "format": "date-time"
                },
                "type": {
                  "type": "string",
                  "enum": [
                    "File Created",
                    "File Modified",
                    "Last Accessed",
                    "Entry Modified"
                  ]
                },
                "source": {
                  "type": "string",
                  "enum": [
                    "NTFS $STANDARD_INFORMATION",
                    "NTFS $FILE_NAME",
                    "OOXML \\docProps\\core.xml"
                  ]
                }
              },
              "required": [
                "timestamp",
                "type",
                "source"
              ],
              "additionalProperties": false
            }
          }
        },
        "required": [
          "timestamps"
        ],
        "additionalProperties": false
      },
      "match": {
        "strings": "casefold_whitespace",
        "list_order": "unordered",
        "timestamps": {
          "/timestamps/*/timestamp": {
            "tolerance_seconds": 2,
            "granularity": "instant"
          }
        }
      }
    },
    {
      "id": "Q37",
      "prompt": "How and when did the suspect print a resignation file?",
      "answer_schema": {
        "type": "object",
        "properties": {
          "output_format": {
            "type": "string"
          },
          "printed_at": {
            "type": "string",
            "format": "date-time"
          },
          "output_path": {
            "type": "string"
          }
        },
        "required": [
          "output_format",
          "printed_at",
          "output_path"
        ],
        "additionalProperties": false
      },
      "match": {
        "strings": "casefold_whitespace",
        "list_order": "unordered",
        "timestamps": {
          "/printed_at": {
            "tolerance_seconds": 2,
            "granularity": "instant"
          }
        }
      }
    },
    {
      "id": "Q38",
      "prompt": "Where are ‘Thumbcache’ files located?",
      "answer_schema": {
        "type": "object",
        "properties": {
          "paths": {
            "type": "array",
            "items": {
              "type": "string"
            }
          }
        },
        "required": [
          "paths"
        ],
        "additionalProperties": false
      },
      "match": {
        "strings": "casefold_whitespace",
        "list_order": "unordered",
        "timestamps": {},
        "paths": {
          "/paths/*": {
            "style": "windows",
            "root": "C:",
            "case_sensitive": false,
            "scope": "PC system volume"
          }
        }
      }
    },
    {
      "id": "Q39",
      "prompt": "Identify traces related to confidential files stored in Thumbcache. (Include ‘256’ only)",
      "answer_schema": {
        "type": "object",
        "properties": {
          "cache": {
            "type": "string"
          },
          "thumbnail_titles": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "thumbnail_artifacts": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "cache_path": {
                  "type": "string"
                },
                "entry_id_or_offset": {
                  "type": "string"
                },
                "image_sha256": {
                  "type": "string"
                },
                "associated_document": {
                  "type": "string"
                },
                "visual_description": {
                  "type": "string"
                },
                "evidence_refs": {
                  "type": "array",
                  "items": {
                    "type": "string"
                  }
                }
              },
              "required": [
                "cache_path",
                "entry_id_or_offset",
                "image_sha256",
                "associated_document",
                "visual_description",
                "evidence_refs"
              ],
              "additionalProperties": false
            }
          }
        },
        "required": [
          "cache",
          "thumbnail_titles",
          "thumbnail_artifacts"
        ],
        "additionalProperties": true,
        "description": "Reference review is unresolved. Supply the full original answer; additional evidence-backed fields are allowed and are retained for review, not automatically graded as wrong."
      },
      "match": {
        "strings": "casefold_whitespace",
        "list_order": "unordered",
        "timestamps": {}
      }
    },
    {
      "id": "Q40",
      "prompt": "Where are Sticky Note files located?",
      "answer_schema": {
        "type": "object",
        "properties": {
          "path": {
            "type": "string"
          }
        },
        "required": [
          "path"
        ],
        "additionalProperties": false
      },
      "match": {
        "strings": "casefold_whitespace",
        "list_order": "unordered",
        "timestamps": {},
        "paths": {
          "/path": {
            "style": "windows",
            "root": "C:",
            "case_sensitive": false,
            "scope": "PC system volume"
          }
        }
      }
    },
    {
      "id": "Q41",
      "prompt": "Identify notes stored in the Sticky Note file.",
      "answer_schema": {
        "type": "object",
        "properties": {
          "notes": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "file_modified": {
                  "type": "string",
                  "format": "date-time"
                },
                "content": {
                  "type": "string"
                }
              },
              "required": [
                "file_modified",
                "content"
              ],
              "additionalProperties": false
            }
          }
        },
        "required": [
          "notes"
        ],
        "additionalProperties": false
      },
      "match": {
        "strings": "casefold_whitespace",
        "list_order": "unordered",
        "timestamps": {
          "/notes/*/file_modified": {
            "tolerance_seconds": 2,
            "granularity": "instant"
          }
        }
      }
    },
    {
      "id": "Q42",
      "prompt": "Was the ‘Windows Search and Indexing’ function enabled? How can you identify it? If it was enabled, what is a file path of the ‘Windows Search’ index database?",
      "answer_schema": {
        "type": "object",
        "properties": {
          "enabled": {
            "type": "boolean"
          },
          "database_path": {
            "type": "string"
          },
          "identification": {
            "type": "object",
            "properties": {
              "database_registry_key": {
                "type": "string"
              },
              "database_registry_value": {
                "type": "string"
              },
              "service_registry_key": {
                "type": "string"
              },
              "startup": {
                "type": "string"
              }
            },
            "required": [
              "database_registry_key",
              "database_registry_value",
              "service_registry_key",
              "startup"
            ],
            "additionalProperties": false
          }
        },
        "required": [
          "enabled",
          "database_path",
          "identification"
        ],
        "additionalProperties": false
      },
      "match": {
        "strings": "casefold_whitespace",
        "list_order": "unordered",
        "timestamps": {}
      }
    },
    {
      "id": "Q43",
      "prompt": "What kinds of data were stored in Windows Search database?",
      "answer_schema": {
        "type": "object",
        "properties": {
          "categories": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "excluded_profile_directory": {
            "type": "string"
          },
          "start_menu_path": {
            "type": "string"
          }
        },
        "required": [
          "categories",
          "excluded_profile_directory",
          "start_menu_path"
        ],
        "additionalProperties": false
      },
      "match": {
        "strings": "casefold_whitespace",
        "list_order": "unordered",
        "timestamps": {}
      }
    },
    {
      "id": "Q44",
      "prompt": "Find traces of Internet Explorer usage stored in Windows Search database. (It should be considered only during a date range between 2015-03-22 and 2015-03-23.)",
      "answer_schema": {
        "type": "object",
        "properties": {
          "records": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "date_modified": {
                  "type": "string",
                  "format": "date-time"
                },
                "url": {
                  "type": "string"
                }
              },
              "required": [
                "date_modified",
                "url"
              ],
              "additionalProperties": false
            }
          }
        },
        "required": [
          "records"
        ],
        "additionalProperties": false
      },
      "match": {
        "strings": "casefold_whitespace",
        "list_order": "unordered",
        "timestamps": {
          "/records/*/date_modified": {
            "tolerance_seconds": 2,
            "granularity": "instant"
          }
        },
        "string_modes": {
          "/records/*/url": "exact"
        }
      }
    },
    {
      "id": "Q45",
      "prompt": "List the e-mail communication stored in Windows Search database. (It should be considered only during a date range between 2015-03-23 and 2015-03-24.)",
      "answer_schema": {
        "type": "object",
        "properties": {
          "messages": {
            "type": "array",
            "items": {
              "anyOf": [
                {
                  "type": "object",
                  "properties": {
                    "timestamp": {
                      "type": "string",
                      "format": "date-time"
                    },
                    "folder_or_recovery_source": {
                      "type": "string"
                    },
                    "from": {
                      "type": "string"
                    },
                    "to": {
                      "type": "string"
                    },
                    "subject": {
                      "type": "string"
                    },
                    "body": {
                      "type": "string"
                    },
                    "attachments": {
                      "type": "array",
                      "items": {}
                    }
                  },
                  "required": [
                    "timestamp",
                    "folder_or_recovery_source",
                    "from",
                    "to",
                    "subject",
                    "body",
                    "attachments"
                  ],
                  "additionalProperties": false
                },
                {
                  "type": "object",
                  "properties": {
                    "timestamp": {
                      "type": "string",
                      "format": "date-time"
                    },
                    "folder_or_recovery_source": {
                      "type": "string"
                    },
                    "from": {
                      "type": "string"
                    },
                    "to": {
                      "type": "string"
                    },
                    "subject": {
                      "type": "string"
                    },
                    "body": {
                      "type": "string"
                    },
                    "attachments": {
                      "type": "array",
                      "items": {
                        "type": "string"
                      }
                    }
                  },
                  "required": [
                    "timestamp",
                    "folder_or_recovery_source",
                    "from",
                    "to",
                    "subject",
                    "body",
                    "attachments"
                  ],
                  "additionalProperties": false
                }
              ]
            }
          }
        },
        "required": [
          "messages"
        ],
        "additionalProperties": false
      },
      "match": {
        "strings": "casefold_whitespace",
        "list_order": "unordered",
        "timestamps": {
          "/messages/*/timestamp": {
            "tolerance_seconds": 2,
            "granularity": "instant"
          }
        }
      }
    },
    {
      "id": "Q46",
      "prompt": "List files and directories related to Windows Desktop stored in Windows Search database. (Windows Desktop directory: \\Users\\informant\\Desktop\\)",
      "answer_schema": {
        "type": "object",
        "properties": {
          "records": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "date_created": {
                  "type": "string",
                  "format": "date-time"
                },
                "path": {
                  "type": "string"
                }
              },
              "required": [
                "date_created",
                "path"
              ],
              "additionalProperties": false
            }
          }
        },
        "required": [
          "records"
        ],
        "additionalProperties": false
      },
      "match": {
        "strings": "casefold_whitespace",
        "list_order": "unordered",
        "timestamps": {
          "/records/*/date_created": {
            "tolerance_seconds": 2,
            "granularity": "instant"
          }
        }
      }
    },
    {
      "id": "Q47",
      "prompt": "Where are Volume Shadow Copies stored? When were they created?",
      "answer_schema": {
        "type": "object",
        "properties": {
          "copies": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "storage_path": {
                  "type": "string"
                },
                "created_at": {
                  "type": "string",
                  "format": "date-time"
                },
                "size_bytes": {
                  "type": "integer"
                },
                "shadow_copy_id": {
                  "type": "string"
                },
                "shadow_copy_set_id": {
                  "type": "string"
                }
              },
              "required": [
                "storage_path",
                "created_at",
                "size_bytes",
                "shadow_copy_id",
                "shadow_copy_set_id"
              ],
              "additionalProperties": false
            }
          }
        },
        "required": [
          "copies"
        ],
        "additionalProperties": false
      },
      "match": {
        "strings": "casefold_whitespace",
        "list_order": "unordered",
        "timestamps": {
          "/copies/*/created_at": {
            "tolerance_seconds": 2,
            "granularity": "instant"
          }
        }
      }
    },
    {
      "id": "Q48",
      "prompt": "Find traces related to Google Drive service in Volume Shadow Copy . What are the differences between the current system image (of Question 29 ~ 31) and its VSC?",
      "answer_schema": {
        "type": "object",
        "properties": {
          "files": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "path": {
                  "type": "string"
                },
                "created_at": {
                  "type": "string",
                  "format": "date-time"
                },
                "modified_at": {
                  "type": "string",
                  "format": "date-time"
                },
                "size_as_printed": {
                  "type": "string",
                  "description": "Displayed size including unit; do not invent byte precision."
                },
                "format": {
                  "type": "string"
                }
              },
              "required": [
                "path",
                "created_at",
                "modified_at",
                "size_as_printed",
                "format"
              ],
              "additionalProperties": false
            }
          },
          "comparison": {
            "type": "object",
            "properties": {
              "last_log_time_in_vsc": {
                "type": "string",
                "format": "date-time"
              },
              "sqlite_files_in_vsc": {
                "type": "array",
                "items": {
                  "type": "string"
                }
              },
              "sqlite_files_deleted_after_logoff": {
                "type": "boolean"
              },
              "deletion_local_date": {
                "type": "string"
              },
              "vsc_created_before_logoff": {
                "type": "boolean"
              }
            },
            "required": [
              "last_log_time_in_vsc",
              "sqlite_files_in_vsc",
              "sqlite_files_deleted_after_logoff",
              "deletion_local_date",
              "vsc_created_before_logoff"
            ],
            "additionalProperties": false
          }
        },
        "required": [
          "files",
          "comparison"
        ],
        "additionalProperties": true,
        "description": "Reference review is unresolved. Supply the full original answer; additional evidence-backed fields are allowed and are retained for review, not automatically graded as wrong."
      },
      "match": {
        "strings": "casefold_whitespace",
        "list_order": "unordered",
        "timestamps": {
          "/files/*/created_at": {
            "tolerance_seconds": 2,
            "granularity": "instant"
          },
          "/files/*/modified_at": {
            "tolerance_seconds": 2,
            "granularity": "instant"
          },
          "/comparison/last_log_time_in_vsc": {
            "tolerance_seconds": 2,
            "granularity": "instant"
          }
        }
      }
    },
    {
      "id": "Q49",
      "prompt": "What files were deleted from Google Drive? Find deleted records of cloud_entry table inside snapshot.db from VSC. (Just examine the SQLite database only. Let us suppose that a text based log file was wiped.) [Hint: DDL of cloud_entry table is as follows.] CREATE TABLE cloud_entry (doc_id TEXT, filename TEXT , modified INTEGER , created INTEGER , acl_role INTEGER , doc_type INTEGER, removed INTEGER , size INTEGER , checksum TEXT , shared INTEGER , resource_type TEXT, PRIMARY KEY (doc_id));",
      "answer_schema": {
        "type": "object",
        "properties": {
          "recovered_records": {
            "type": "array",
            "items": {
              "anyOf": [
                {
                  "type": "object",
                  "properties": {
                    "file_offset": {
                      "type": "integer"
                    },
                    "record_size": {
                      "type": "integer"
                    },
                    "row_id": {
                      "type": "integer"
                    },
                    "header_size": {
                      "type": "integer"
                    },
                    "overwritten_prefix_bytes": {
                      "type": "integer"
                    },
                    "doc_id": {
                      "type": "string"
                    },
                    "filename": {
                      "type": "string"
                    },
                    "modified": {
                      "type": "integer"
                    },
                    "created": {
                      "type": "integer"
                    },
                    "acl_role": {
                      "type": "integer"
                    },
                    "doc_type": {
                      "type": "integer"
                    },
                    "removed": {
                      "type": "integer"
                    },
                    "size": {
                      "type": "integer"
                    },
                    "checksum": {
                      "type": "string"
                    },
                    "shared": {
                      "type": "integer"
                    },
                    "resource_type": {
                      "type": "string"
                    }
                  },
                  "required": [
                    "file_offset",
                    "record_size",
                    "row_id",
                    "header_size",
                    "overwritten_prefix_bytes",
                    "doc_id",
                    "filename",
                    "modified",
                    "created",
                    "acl_role",
                    "doc_type",
                    "removed",
                    "size",
                    "checksum",
                    "shared",
                    "resource_type"
                  ],
                  "additionalProperties": false
                },
                {
                  "type": "object",
                  "properties": {
                    "file_offset": {
                      "type": "integer"
                    },
                    "record_size": {
                      "type": [
                        "string",
                        "number",
                        "boolean",
                        "object",
                        "array",
                        "null"
                      ],
                      "description": "Use null only for a source-reported absent/unavailable value; use unknown status if the system cannot answer."
                    },
                    "row_id": {
                      "type": [
                        "string",
                        "number",
                        "boolean",
                        "object",
                        "array",
                        "null"
                      ],
                      "description": "Use null only for a source-reported absent/unavailable value; use unknown status if the system cannot answer."
                    },
                    "header_size": {
                      "type": [
                        "string",
                        "number",
                        "boolean",
                        "object",
                        "array",
                        "null"
                      ],
                      "description": "Use null only for a source-reported absent/unavailable value; use unknown status if the system cannot answer."
                    },
                    "overwritten_prefix_bytes": {
                      "type": "integer"
                    },
                    "doc_id": {
                      "type": "string"
                    },
                    "filename": {
                      "type": "string"
                    },
                    "modified": {
                      "type": "integer"
                    },
                    "created": {
                      "type": "integer"
                    },
                    "acl_role": {
                      "type": "integer"
                    },
                    "doc_type": {
                      "type": "integer"
                    },
                    "removed": {
                      "type": "integer"
                    },
                    "size": {
                      "type": "integer"
                    },
                    "checksum": {
                      "type": "string"
                    },
                    "shared": {
                      "type": "integer"
                    },
                    "resource_type": {
                      "type": "string"
                    }
                  },
                  "required": [
                    "file_offset",
                    "record_size",
                    "row_id",
                    "header_size",
                    "overwritten_prefix_bytes",
                    "doc_id",
                    "filename",
                    "modified",
                    "created",
                    "acl_role",
                    "doc_type",
                    "removed",
                    "size",
                    "checksum",
                    "shared",
                    "resource_type"
                  ],
                  "additionalProperties": false
                }
              ]
            }
          }
        },
        "required": [
          "recovered_records"
        ],
        "additionalProperties": false
      },
      "match": {
        "strings": "casefold_whitespace",
        "list_order": "unordered",
        "timestamps": {}
      }
    },
    {
      "id": "Q50",
      "prompt": "Why can’t we find Outlook’s e-mail data in Volume Shadow Copy?",
      "answer_schema": {
        "type": "object",
        "properties": {
          "ost_files_excluded": {
            "type": "boolean"
          },
          "registry_key": {
            "type": "string"
          },
          "value_name": {
            "type": "string"
          },
          "pattern": {
            "type": "string"
          }
        },
        "required": [
          "ost_files_excluded",
          "registry_key",
          "value_name",
          "pattern"
        ],
        "additionalProperties": false
      },
      "match": {
        "strings": "casefold_whitespace",
        "list_order": "unordered",
        "timestamps": {}
      }
    },
    {
      "id": "Q51",
      "prompt": "Examine ‘Recycle Bin’ data in PC.",
      "answer_schema": {
        "type": "object",
        "properties": {
          "records": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "i_filename": {
                  "type": "string"
                },
                "deleted_at": {
                  "type": "string",
                  "format": "date-time"
                },
                "original_path": {
                  "type": "string"
                }
              },
              "required": [
                "i_filename",
                "deleted_at",
                "original_path"
              ],
              "additionalProperties": false
            }
          }
        },
        "required": [
          "records"
        ],
        "additionalProperties": false
      },
      "match": {
        "strings": "casefold_whitespace",
        "list_order": "unordered",
        "timestamps": {
          "/records/*/deleted_at": {
            "tolerance_seconds": 2,
            "granularity": "instant"
          }
        }
      }
    },
    {
      "id": "Q52",
      "prompt": "What actions were performed for anti-forensics on PC at the last day ‘2015-03-25’?",
      "answer_schema": {
        "type": "object",
        "properties": {
          "actions": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "timestamp": {
                  "type": "string",
                  "format": "date-time"
                },
                "action": {
                  "type": "string"
                },
                "target": {
                  "type": "string"
                }
              },
              "required": [
                "timestamp",
                "action",
                "target"
              ],
              "additionalProperties": false
            }
          },
          "wiping": {
            "type": "object",
            "properties": {
              "start": {
                "type": "string",
                "format": "date-time"
              },
              "end": {
                "type": "string",
                "format": "date-time"
              },
              "tool": {
                "type": "string"
              },
              "paths": {
                "type": "array",
                "items": {
                  "type": "string"
                }
              }
            },
            "required": [
              "start",
              "end",
              "tool",
              "paths"
            ],
            "additionalProperties": false
          },
          "shift_delete": {
            "type": "object",
            "properties": {
              "timestamp": {
                "type": "string",
                "format": "date-time"
              },
              "paths": {
                "type": "array",
                "items": {
                  "type": "string"
                }
              }
            },
            "required": [
              "timestamp",
              "paths"
            ],
            "additionalProperties": false
          },
          "deleted_mail_subjects": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "mail_deletion_timestamp": {
            "type": [
              "string",
              "number",
              "boolean",
              "object",
              "array",
              "null"
            ],
            "description": "Use null only for a source-reported absent/unavailable value; use unknown status if the system cannot answer."
          },
          "wipe_trace": {
            "type": "object",
            "properties": {
              "terminal_file_deleted": {
                "type": "boolean"
              },
              "erasure_method": {
                "type": "string"
              },
              "passes": {
                "type": "integer"
              },
              "steps": {
                "type": "array",
                "items": {
                  "type": "object",
                  "properties": {
                    "step": {
                      "type": "integer"
                    },
                    "filename": {
                      "type": "string"
                    }
                  },
                  "required": [
                    "step",
                    "filename"
                  ],
                  "additionalProperties": false
                }
              }
            },
            "required": [
              "terminal_file_deleted",
              "erasure_method",
              "passes",
              "steps"
            ],
            "additionalProperties": false
          }
        },
        "required": [
          "actions",
          "wiping",
          "shift_delete",
          "deleted_mail_subjects",
          "mail_deletion_timestamp",
          "wipe_trace"
        ],
        "additionalProperties": false
      },
      "match": {
        "strings": "casefold_whitespace",
        "list_order": "unordered",
        "timestamps": {
          "/actions/*/timestamp": {
            "tolerance_seconds": 2,
            "granularity": "instant"
          },
          "/wiping/start": {
            "tolerance_seconds": 2,
            "granularity": "instant"
          },
          "/wiping/end": {
            "tolerance_seconds": 2,
            "granularity": "instant"
          },
          "/shift_delete/timestamp": {
            "tolerance_seconds": 2,
            "granularity": "instant"
          }
        },
        "string_modes": {
          "/wipe_trace/steps/*/filename": "exact"
        }
      }
    },
    {
      "id": "Q53",
      "prompt": "Recover deleted files from USB drive ‘RM#2’.",
      "answer_schema": {
        "type": "object",
        "properties": {
          "files": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "path": {
                  "type": "string"
                },
                "format": {
                  "type": "string"
                },
                "size_as_printed": {
                  "type": "string",
                  "description": "Displayed size including unit; do not invent byte precision."
                },
                "viewable": {
                  "type": "boolean"
                },
                "recovery_method": {
                  "type": "string"
                }
              },
              "required": [
                "path",
                "format",
                "size_as_printed",
                "viewable",
                "recovery_method"
              ],
              "additionalProperties": false
            }
          },
          "optional_carving": {
            "type": "object",
            "properties": {
              "other_files_related_to_scenario": {
                "type": "boolean"
              },
              "reported_formats": {
                "type": "array",
                "items": {
                  "type": "string"
                }
              }
            },
            "required": [
              "other_files_related_to_scenario",
              "reported_formats"
            ],
            "additionalProperties": false
          },
          "carving_results": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "recovered_artifact": {
                  "type": "string"
                },
                "format": {
                  "type": "string"
                },
                "size_bytes": {
                  "type": "integer"
                },
                "relation_to_case": {
                  "type": "string"
                },
                "basis": {
                  "type": "string"
                },
                "evidence_refs": {
                  "type": "array",
                  "items": {
                    "type": "string"
                  }
                }
              },
              "required": [
                "recovered_artifact",
                "format",
                "size_bytes",
                "relation_to_case",
                "basis",
                "evidence_refs"
              ],
              "additionalProperties": false
            },
            "description": "Optional actual carving inventory; source examples must not be mistaken for an exhaustive list."
          }
        },
        "required": [
          "files"
        ],
        "additionalProperties": true,
        "description": "Reference review is unresolved. Supply the full original answer; additional evidence-backed fields are allowed and are retained for review, not automatically graded as wrong."
      },
      "match": {
        "strings": "casefold_whitespace",
        "list_order": "unordered",
        "timestamps": {}
      }
    },
    {
      "id": "Q54",
      "prompt": "What actions were performed for anti-forensics on USB drive ‘RM#2’? [Hint: this can be inferred from the results of Question 53.]",
      "answer_schema": {
        "type": "object",
        "properties": {
          "action": {
            "type": "string"
          },
          "purpose": {
            "type": "string"
          }
        },
        "required": [
          "action",
          "purpose"
        ],
        "additionalProperties": false
      },
      "match": {
        "strings": "casefold_whitespace",
        "list_order": "unordered",
        "timestamps": {}
      }
    },
    {
      "id": "Q55",
      "prompt": "What files were copied from PC to USB drive ‘RM#2’?",
      "answer_schema": {
        "type": "object",
        "properties": {
          "files": {
            "type": "array",
            "items": {
              "anyOf": [
                {
                  "type": "object",
                  "properties": {
                    "filename": {
                      "type": "string"
                    },
                    "format": {
                      "type": "string"
                    },
                    "size_as_printed": {
                      "type": "string",
                      "description": "Displayed size including unit; do not invent byte precision."
                    },
                    "pc_jumplist_or_shellbag_entry": {
                      "type": [
                        "string",
                        "number",
                        "boolean",
                        "object",
                        "array",
                        "null"
                      ],
                      "description": "Use null only for a source-reported absent/unavailable value; use unknown status if the system cannot answer."
                    }
                  },
                  "required": [
                    "filename",
                    "format",
                    "size_as_printed",
                    "pc_jumplist_or_shellbag_entry"
                  ],
                  "additionalProperties": false
                },
                {
                  "type": "object",
                  "properties": {
                    "filename": {
                      "type": "string"
                    },
                    "format": {
                      "type": "string"
                    },
                    "size_as_printed": {
                      "type": "string",
                      "description": "Displayed size including unit; do not invent byte precision."
                    },
                    "pc_jumplist_or_shellbag_entry": {
                      "type": "string"
                    }
                  },
                  "required": [
                    "filename",
                    "format",
                    "size_as_printed",
                    "pc_jumplist_or_shellbag_entry"
                  ],
                  "additionalProperties": false
                }
              ]
            }
          }
        },
        "required": [
          "files"
        ],
        "additionalProperties": false
      },
      "match": {
        "strings": "casefold_whitespace",
        "list_order": "unordered",
        "timestamps": {}
      }
    },
    {
      "id": "Q56",
      "prompt": "Recover hidden files from the CD-R ‘RM#3’. How to determine proper filenames of the original files prior to renaming tasks?",
      "answer_schema": {
        "type": "object",
        "properties": {
          "recovery_method": {
            "type": "string"
          },
          "filename_basis": {
            "type": "string"
          },
          "files": {
            "type": "array",
            "items": {
              "anyOf": [
                {
                  "type": "object",
                  "properties": {
                    "inferred_filename": {
                      "type": "string"
                    },
                    "format": {
                      "type": "string"
                    },
                    "size_as_printed": {
                      "type": "string",
                      "description": "Displayed size including unit; do not invent byte precision."
                    },
                    "viewability": {
                      "type": "string"
                    }
                  },
                  "required": [
                    "inferred_filename",
                    "format",
                    "size_as_printed",
                    "viewability"
                  ],
                  "additionalProperties": false
                },
                {
                  "type": "object",
                  "properties": {
                    "inferred_filename": {
                      "type": "string"
                    },
                    "format": {
                      "type": "string"
                    },
                    "size_as_printed": {
                      "type": [
                        "string",
                        "number",
                        "boolean",
                        "object",
                        "array",
                        "null"
                      ],
                      "description": "Use null only for a source-reported absent/unavailable value; use unknown status if the system cannot answer."
                    },
                    "viewability": {
                      "type": "string"
                    }
                  },
                  "required": [
                    "inferred_filename",
                    "format",
                    "size_as_printed",
                    "viewability"
                  ],
                  "additionalProperties": false
                }
              ]
            }
          }
        },
        "required": [
          "recovery_method",
          "filename_basis",
          "files"
        ],
        "additionalProperties": false
      },
      "match": {
        "strings": "casefold_whitespace",
        "list_order": "unordered",
        "timestamps": {}
      }
    },
    {
      "id": "Q57",
      "prompt": "What actions were performed for anti-forensics on CD-R ‘RM#3’?",
      "answer_schema": {
        "type": "object",
        "properties": {
          "actions": {
            "type": "array",
            "items": {
              "anyOf": [
                {
                  "type": "object",
                  "properties": {
                    "step": {
                      "type": "integer"
                    },
                    "action": {
                      "type": "string"
                    },
                    "method": {
                      "type": "string"
                    }
                  },
                  "required": [
                    "step",
                    "action",
                    "method"
                  ],
                  "additionalProperties": false
                },
                {
                  "type": "object",
                  "properties": {
                    "step": {
                      "type": "integer"
                    },
                    "action": {
                      "type": "string"
                    },
                    "file_groups": {
                      "type": "array",
                      "items": {
                        "type": "string"
                      }
                    }
                  },
                  "required": [
                    "step",
                    "action",
                    "file_groups"
                  ],
                  "additionalProperties": false
                },
                {
                  "type": "object",
                  "properties": {
                    "step": {
                      "type": "integer"
                    },
                    "action": {
                      "type": "string"
                    },
                    "purpose": {
                      "type": "string"
                    }
                  },
                  "required": [
                    "step",
                    "action",
                    "purpose"
                  ],
                  "additionalProperties": false
                }
              ]
            }
          }
        },
        "required": [
          "actions"
        ],
        "additionalProperties": false
      },
      "match": {
        "strings": "casefold_whitespace",
        "list_order": "unordered",
        "timestamps": {}
      }
    },
    {
      "id": "Q58",
      "prompt": "Create a detailed timeline of data leakage processes.",
      "answer_schema": {
        "type": "object",
        "properties": {
          "daily_summary": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "date": {
                  "type": "string"
                },
                "activity": {
                  "type": "string"
                }
              },
              "required": [
                "date",
                "activity"
              ],
              "additionalProperties": false
            }
          },
          "events": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "time_or_interval": {
                  "type": "string"
                },
                "action": {
                  "type": "string"
                },
                "entities": {
                  "type": "array",
                  "items": {
                    "type": "string"
                  }
                },
                "evidence_refs": {
                  "type": "array",
                  "items": {
                    "type": "string"
                  }
                },
                "uncertainty": {
                  "type": "string"
                }
              },
              "required": [
                "time_or_interval",
                "action",
                "entities",
                "evidence_refs",
                "uncertainty"
              ],
              "additionalProperties": false
            },
            "description": "Detailed evidence-linked events covering the requested leakage process; a daily summary alone does not answer the prompt."
          }
        },
        "required": [
          "events"
        ],
        "additionalProperties": true,
        "description": "Reference review is unresolved. Supply the full original answer; additional evidence-backed fields are allowed and are retained for review, not automatically graded as wrong."
      },
      "match": {
        "strings": "casefold_whitespace",
        "list_order": "unordered",
        "timestamps": {}
      }
    },
    {
      "id": "Q59",
      "prompt": "List and explain methodologies of data leakage performed by the suspect.",
      "answer_schema": {
        "type": "object",
        "properties": {
          "network_transmission": {
            "type": "object",
            "properties": {
              "email_attachment": {
                "type": "object",
                "properties": {
                  "local_minute": {
                    "type": "string",
                    "description": "Local date/time at minute precision, YYYY-MM-DD HH:MM in the declared case timezone."
                  },
                  "filename": {
                    "type": "string"
                  }
                },
                "required": [
                  "local_minute",
                  "filename"
                ],
                "additionalProperties": false
              },
              "email_shared_links": {
                "type": "object",
                "properties": {
                  "local_minute": {
                    "type": "string",
                    "description": "Local date/time at minute precision, YYYY-MM-DD HH:MM in the declared case timezone."
                  },
                  "content": {
                    "type": "string"
                  }
                },
                "required": [
                  "local_minute",
                  "content"
                ],
                "additionalProperties": false
              },
              "cloud_storage": {
                "type": "object",
                "properties": {
                  "local_minute": {
                    "type": "string",
                    "description": "Local date/time at minute precision, YYYY-MM-DD HH:MM in the declared case timezone."
                  },
                  "filenames": {
                    "type": "array",
                    "items": {
                      "type": "string"
                    }
                  }
                },
                "required": [
                  "local_minute",
                  "filenames"
                ],
                "additionalProperties": false
              }
            },
            "required": [
              "email_attachment",
              "email_shared_links",
              "cloud_storage"
            ],
            "additionalProperties": false
          },
          "storage_device": {
            "type": "object",
            "properties": {
              "usb_flash_drive": {
                "type": "object",
                "properties": {
                  "start_local_minute": {
                    "type": "string",
                    "description": "Local date/time at minute precision, YYYY-MM-DD HH:MM in the declared case timezone."
                  },
                  "end_local_minute": {
                    "type": "string",
                    "description": "Local date/time at minute precision, YYYY-MM-DD HH:MM in the declared case timezone."
                  },
                  "example_filename": {
                    "type": "string"
                  },
                  "partition_formatted": {
                    "type": "boolean"
                  },
                  "copied_files_remain_in_unused_area": {
                    "type": "boolean"
                  }
                },
                "required": [
                  "start_local_minute",
                  "end_local_minute",
                  "example_filename",
                  "partition_formatted",
                  "copied_files_remain_in_unused_area"
                ],
                "additionalProperties": false
              },
              "cd_r": {
                "type": "object",
                "properties": {
                  "start_local_minute": {
                    "type": "string",
                    "description": "Local date/time at minute precision, YYYY-MM-DD HH:MM in the declared case timezone."
                  },
                  "end_local_minute": {
                    "type": "string",
                    "description": "Local date/time at minute precision, YYYY-MM-DD HH:MM in the declared case timezone."
                  },
                  "confidential_file_count": {
                    "type": "integer"
                  },
                  "example_filename": {
                    "type": "string"
                  },
                  "confidential_files_deleted": {
                    "type": "boolean"
                  },
                  "files_remain_in_unused_area": {
                    "type": "boolean"
                  }
                },
                "required": [
                  "start_local_minute",
                  "end_local_minute",
                  "confidential_file_count",
                  "example_filename",
                  "confidential_files_deleted",
                  "files_remain_in_unused_area"
                ],
                "additionalProperties": false
              }
            },
            "required": [
              "usb_flash_drive",
              "cd_r"
            ],
            "additionalProperties": false
          }
        },
        "required": [
          "network_transmission",
          "storage_device"
        ],
        "additionalProperties": false
      },
      "match": {
        "strings": "casefold_whitespace",
        "list_order": "unordered",
        "timestamps": {}
      }
    },
    {
      "id": "Q60",
      "prompt": "Create a visual diagram for a summary of results.",
      "answer_schema": {
        "type": "object",
        "properties": {
          "artifact_type": {
            "type": "string"
          },
          "source_example": {
            "type": "string"
          },
          "diagram": {
            "type": "object",
            "properties": {
              "format": {
                "type": "string"
              },
              "content": {
                "type": "string"
              },
              "evidence_refs": {
                "type": "array",
                "items": {
                  "type": "string"
                }
              }
            },
            "required": [
              "format",
              "content",
              "evidence_refs"
            ],
            "additionalProperties": false,
            "description": "Provide the actual visual diagram or a portable diagram specification. A label naming a source example is not a diagram."
          }
        },
        "required": [
          "diagram"
        ],
        "additionalProperties": true,
        "description": "Reference review is unresolved. Supply the full original answer; additional evidence-backed fields are allowed and are retained for review, not automatically graded as wrong."
      },
      "match": {
        "strings": "casefold_whitespace",
        "list_order": "unordered",
        "timestamps": {}
      }
    }
  ],
  "contract_revision": "author-visual-review-1"
}
```
