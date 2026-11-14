import ChainOfProof
open ChainOfProof

namespace Cert.A043

def cited : List Fact := [
  ⟨242, .webSearch, 1427134355567263, 1, 142, 126⟩ ]

def claim : Claim := Sets.searched 242

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A043

#print axioms Cert.A043.verified
