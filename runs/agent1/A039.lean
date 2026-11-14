import ChainOfProof
open ChainOfProof

namespace Cert.A039

def cited : List Fact := [
  ⟨137, .webSearch, 1427134078080700, 1, 80, 70⟩ ]

def claim : Claim := Sets.searched 137

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A039

#print axioms Cert.A039.verified
