import ChainOfProof
open ChainOfProof

namespace Cert.A095

def cited : List Fact := [
  ⟨21, .lnkTarget, 1427135840499256, 1, 18, 19⟩,
  ⟨8134, .fileRenamed, 1427136100269314, 1, 12121, 12122⟩ ]

def claim : Claim := .before 21 8134

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A095

#print axioms Cert.A095.verified
