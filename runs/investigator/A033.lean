import ChainOfProof
open ChainOfProof

namespace Cert.A033

def cited : List Fact := [
  ⟨232, .webSearch, 1427134077288696, 1, 135, 126⟩ ]

def claim : Claim := Sets.searched 232

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A033

#print axioms Cert.A033.verified
