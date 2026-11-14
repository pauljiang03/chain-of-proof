import ChainOfProof
open ChainOfProof

namespace Cert.A068

def cited : List Fact := [
  ⟨166, .webSearch, 1427143432477705, 1, 89, 70⟩ ]

def claim : Claim := Sets.searched 166

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A068

#print axioms Cert.A068.verified
