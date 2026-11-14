import ChainOfProof
open ChainOfProof

namespace Cert.A097

def cited : List Fact := [
  ⟨31, .lnkTarget, 1427142413783793, 1, 25, 26⟩,
  ⟨8864, .fileRenamed, 1427142644624013, 1, 12526, 12527⟩ ]

def claim : Claim := .before 31 8864

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A097

#print axioms Cert.A097.verified
