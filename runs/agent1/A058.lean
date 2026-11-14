import ChainOfProof
open ChainOfProof

namespace Cert.A058

def cited : List Fact := [
  ⟨156, .webSearch, 1427134695855272, 1, 94, 69⟩ ]

def claim : Claim := Sets.searched 156

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A058

#print axioms Cert.A058.verified
