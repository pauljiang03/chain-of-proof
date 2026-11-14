import ChainOfProof
open ChainOfProof

namespace Cert.A070

def cited : List Fact := [
  ⟨269, .webSearch, 1427144108521080, 1, 159, 126⟩ ]

def claim : Claim := Sets.searched 269

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A070

#print axioms Cert.A070.verified
