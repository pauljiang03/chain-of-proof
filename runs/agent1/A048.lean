import ChainOfProof
open ChainOfProof

namespace Cert.A048

def cited : List Fact := [
  ⟨146, .webSearch, 1427134355567263, 1, 86, 70⟩ ]

def claim : Claim := Sets.searched 146

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A048

#print axioms Cert.A048.verified
