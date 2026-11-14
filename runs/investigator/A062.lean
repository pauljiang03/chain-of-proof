import ChainOfProof
open ChainOfProof

namespace Cert.A062

def cited : List Fact := [
  ⟨261, .webSearch, 1427143427512482, 1, 145, 126⟩ ]

def claim : Claim := Sets.searched 261

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A062

#print axioms Cert.A062.verified
