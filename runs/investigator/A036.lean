import ChainOfProof
open ChainOfProof

namespace Cert.A036

def cited : List Fact := [
  ⟨235, .webSearch, 1427134103642269, 1, 136, 126⟩ ]

def claim : Claim := Sets.searched 235

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A036

#print axioms Cert.A036.verified
