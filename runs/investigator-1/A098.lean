import ChainOfProof
open ChainOfProof

namespace Cert.A098

def cited : List Fact := [
  ⟨8864, .fileRenamed, 1427142644624013, 1, 12526, 12527⟩,
  ⟨2290, .cloudFile, 1427142757552000, 1000, 1422, 1429⟩ ]

def claim : Claim := .before 8864 2290

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A098

#print axioms Cert.A098.verified
