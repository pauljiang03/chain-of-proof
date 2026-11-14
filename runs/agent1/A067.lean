import ChainOfProof
open ChainOfProof

namespace Cert.A067

def cited : List Fact := [
  ⟨165, .webSearch, 1427143427512482, 1, 89, 70⟩ ]

def claim : Claim := Sets.searched 165

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A067

#print axioms Cert.A067.verified
