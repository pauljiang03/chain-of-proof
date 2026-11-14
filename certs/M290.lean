import ChainOfProof
open ChainOfProof

namespace Cert.M290

def cited : List Fact := [
  ⟨10970, .fileSeen, 1247547429625211, 1, 15434, 15339⟩,
  ⟨10971, .fileSeen, 1247547432043215, 1, 15435, 15339⟩,
  ⟨10972, .fileSeen, 1247547432090015, 1, 15436, 15339⟩,
  ⟨10973, .fileSeen, 1247547432168015, 1, 15437, 15339⟩,
  ⟨10974, .fileSeen, 1247547432230415, 1, 15438, 15339⟩,
  ⟨10975, .fileSeen, 1247547432246015, 1, 15438, 15339⟩,
  ⟨10976, .fileSeen, 1247547432277215, 1, 15439, 15339⟩,
  ⟨10977, .fileSeen, 1247547432292815, 1, 15439, 15339⟩,
  ⟨10978, .fileSeen, 1247547433540818, 1, 15424, 15339⟩,
  ⟨10979, .fileSeen, 1247547433618818, 1, 15440, 15339⟩,
  ⟨10980, .fileSeen, 1247547433634418, 1, 15441, 15339⟩,
  ⟨10981, .fileSeen, 1247547433650018, 1, 15442, 15339⟩,
  ⟨10982, .fileSeen, 1247547433650018, 1, 15443, 15339⟩,
  ⟨10983, .fileSeen, 1247547433665618, 1, 15442, 15339⟩,
  ⟨10984, .fileSeen, 1247547433665618, 1, 15443, 15339⟩,
  ⟨10985, .fileSeen, 1247547433665618, 1, 15441, 15339⟩,
  ⟨10986, .fileSeen, 1247547674046440, 1, 15355, 15339⟩,
  ⟨10987, .fileSeen, 1247547674046440, 1, 15444, 15339⟩,
  ⟨10988, .fileSeen, 1247547674046440, 1, 15376, 15339⟩,
  ⟨10989, .fileSeen, 1247548136521236, 1, 15363, 15339⟩,
  ⟨10990, .fileSeen, 1247548136614837, 1, 15366, 15339⟩,
  ⟨10991, .fileSeen, 1247549551565339, 1, 15445, 15339⟩,
  ⟨10992, .fileSeen, 1247549551612139, 1, 15445, 15339⟩,
  ⟨10993, .fileSeen, 1247549551612139, 1, 15405, 15339⟩,
  ⟨10994, .fileSeen, 1247549551627739, 1, 15446, 15339⟩,
  ⟨10995, .fileSeen, 1247549551627739, 1, 15447, 15339⟩,
  ⟨10996, .fileSeen, 1247549551643339, 1, 15448, 15339⟩,
  ⟨10997, .fileSeen, 1247549551643339, 1, 15446, 15339⟩,
  ⟨10998, .fileSeen, 1247549551658939, 1, 15448, 15339⟩,
  ⟨10999, .fileSeen, 1247549551658939, 1, 15407, 15339⟩,
  ⟨11000, .fileSeen, 1247549551658939, 1, 15449, 15339⟩,
  ⟨11001, .fileSeen, 1247549551658939, 1, 15450, 15339⟩,
  ⟨11002, .fileSeen, 1247549551658939, 1, 15451, 15339⟩,
  ⟨11003, .fileSeen, 1247549551658939, 1, 15452, 15339⟩,
  ⟨11004, .fileSeen, 1247549551658939, 1, 13957, 15453⟩,
  ⟨11005, .fileSeen, 1247549551658939, 1, 13957, 15339⟩,
  ⟨11006, .fileSeen, 1247549551658939, 1, 13965, 15453⟩,
  ⟨11007, .fileSeen, 1247549551658939, 1, 13965, 15339⟩,
  ⟨11008, .fileSeen, 1247549551658939, 1, 13988, 15453⟩,
  ⟨11009, .fileSeen, 1247549551658939, 1, 13988, 15339⟩ ]

def claim : Claim := .both (Sets.fileRecorded 10970) (.both (Sets.fileRecorded 10971) (.both (Sets.fileRecorded 10972) (.both (Sets.fileRecorded 10973) (.both (Sets.fileRecorded 10974) (.both (Sets.fileRecorded 10975) (.both (Sets.fileRecorded 10976) (.both (Sets.fileRecorded 10977) (.both (Sets.fileRecorded 10978) (.both (Sets.fileRecorded 10979) (.both (Sets.fileRecorded 10980) (.both (Sets.fileRecorded 10981) (.both (Sets.fileRecorded 10982) (.both (Sets.fileRecorded 10983) (.both (Sets.fileRecorded 10984) (.both (Sets.fileRecorded 10985) (.both (Sets.fileRecorded 10986) (.both (Sets.fileRecorded 10987) (.both (Sets.fileRecorded 10988) (.both (Sets.fileRecorded 10989) (.both (Sets.fileRecorded 10990) (.both (Sets.fileRecorded 10991) (.both (Sets.fileRecorded 10992) (.both (Sets.fileRecorded 10993) (.both (Sets.fileRecorded 10994) (.both (Sets.fileRecorded 10995) (.both (Sets.fileRecorded 10996) (.both (Sets.fileRecorded 10997) (.both (Sets.fileRecorded 10998) (.both (Sets.fileRecorded 10999) (.both (Sets.fileRecorded 11000) (.both (Sets.fileRecorded 11001) (.both (Sets.fileRecorded 11002) (.both (Sets.fileRecorded 11003) (.both (Sets.fileRecorded 11004) (.both (Sets.fileRecorded 11005) (.both (Sets.fileRecorded 11006) (.both (Sets.fileRecorded 11007) (.both (Sets.fileRecorded 11008) (Sets.fileRecorded 11009)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M290

#print axioms Cert.M290.verified
