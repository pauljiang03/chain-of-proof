import ChainOfProof
open ChainOfProof

namespace Cert.A012

def cited : List Fact := [
  ⟨211, .webSearch, 1427037863631855, 1, 124, 126⟩ ]

def claim : Claim := Sets.searched 211

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A012

#print axioms Cert.A012.verified
