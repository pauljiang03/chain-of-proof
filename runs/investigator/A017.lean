import ChainOfProof
open ChainOfProof

namespace Cert.A017

def cited : List Fact := [
  ⟨216, .webSearch, 1427131676613960, 1, 129, 125⟩ ]

def claim : Claim := Sets.searched 216

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A017

#print axioms Cert.A017.verified
