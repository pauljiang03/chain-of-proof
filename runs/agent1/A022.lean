import ChainOfProof
open ChainOfProof

namespace Cert.A022

def cited : List Fact := [
  ⟨120, .webSearch, 1427131676613960, 1, 73, 69⟩ ]

def claim : Claim := Sets.searched 120

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A022

#print axioms Cert.A022.verified
