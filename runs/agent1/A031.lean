import ChainOfProof
open ChainOfProof

namespace Cert.A031

def cited : List Fact := [
  ⟨129, .webSearch, 1427133919638342, 1, 76, 69⟩ ]

def claim : Claim := Sets.searched 129

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A031

#print axioms Cert.A031.verified
