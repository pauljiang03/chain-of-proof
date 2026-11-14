import ChainOfProof
open ChainOfProof

namespace Cert.A054

def cited : List Fact := [
  ⟨108, .fileCreated, 1427205567120000, 10000, 92, 69⟩,
  ⟨376, .unallocatedOnDevice, 1794614400000000, 1, 2, 69⟩,
  ⟨109, .fileCreated, 1427205577630000, 10000, 93, 69⟩,
  ⟨110, .fileCreated, 1427205579580000, 10000, 94, 69⟩,
  ⟨111, .fileCreated, 1427205579680000, 10000, 95, 69⟩,
  ⟨112, .fileCreated, 1427205579710000, 10000, 96, 69⟩,
  ⟨113, .fileCreated, 1427205580710000, 10000, 97, 69⟩,
  ⟨114, .fileCreated, 1427205583520000, 10000, 98, 69⟩,
  ⟨115, .fileCreated, 1427205583550000, 10000, 99, 69⟩,
  ⟨116, .fileCreated, 1427205584810000, 10000, 100, 69⟩,
  ⟨117, .fileCreated, 1427205584860000, 10000, 101, 69⟩,
  ⟨118, .fileCreated, 1427205606780000, 10000, 102, 69⟩,
  ⟨119, .fileCreated, 1427205612590000, 10000, 103, 69⟩,
  ⟨120, .fileCreated, 1427205612970000, 10000, 104, 69⟩,
  ⟨121, .fileCreated, 1427205613550000, 10000, 105, 69⟩,
  ⟨122, .fileCreated, 1427205614340000, 10000, 106, 69⟩,
  ⟨123, .fileCreated, 1427205615650000, 10000, 107, 69⟩,
  ⟨124, .fileCreated, 1427205618410000, 10000, 108, 69⟩ ]

def claim : Claim := .both (Sets.recoveredOnDevice 108 376) (.both (Sets.recoveredOnDevice 109 376) (.both (Sets.recoveredOnDevice 110 376) (.both (Sets.recoveredOnDevice 111 376) (.both (Sets.recoveredOnDevice 112 376) (.both (Sets.recoveredOnDevice 113 376) (.both (Sets.recoveredOnDevice 114 376) (.both (Sets.recoveredOnDevice 115 376) (.both (Sets.recoveredOnDevice 116 376) (.both (Sets.recoveredOnDevice 117 376) (.both (Sets.recoveredOnDevice 118 376) (.both (Sets.recoveredOnDevice 119 376) (.both (Sets.recoveredOnDevice 120 376) (.both (Sets.recoveredOnDevice 121 376) (.both (Sets.recoveredOnDevice 122 376) (.both (Sets.recoveredOnDevice 123 376) (Sets.recoveredOnDevice 124 376))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A054

#print axioms Cert.A054.verified
