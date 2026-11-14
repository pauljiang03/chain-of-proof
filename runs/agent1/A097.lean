import ChainOfProof
open ChainOfProof

namespace Cert.A097

def cited : List Fact := [
  ⟨195, .webSearch, 1427294804771004, 1, 112, 70⟩ ]

def claim : Claim := Sets.searched 195

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A097

#print axioms Cert.A097.verified
