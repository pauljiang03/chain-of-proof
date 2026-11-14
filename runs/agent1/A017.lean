import ChainOfProof
open ChainOfProof

namespace Cert.A017

def cited : List Fact := [
  ⟨115, .webSearch, 1427037863631855, 1, 68, 70⟩ ]

def claim : Claim := Sets.searched 115

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A017

#print axioms Cert.A017.verified
