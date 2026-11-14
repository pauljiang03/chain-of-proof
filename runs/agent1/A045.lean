import ChainOfProof
open ChainOfProof

namespace Cert.A045

def cited : List Fact := [
  ⟨143, .webSearch, 1427134203820419, 1, 83, 70⟩ ]

def claim : Claim := Sets.searched 143

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A045

#print axioms Cert.A045.verified
