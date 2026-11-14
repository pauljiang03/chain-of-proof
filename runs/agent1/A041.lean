import ChainOfProof
open ChainOfProof

namespace Cert.A041

def cited : List Fact := [
  ⟨139, .webSearch, 1427134103642269, 1, 80, 70⟩ ]

def claim : Claim := Sets.searched 139

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A041

#print axioms Cert.A041.verified
