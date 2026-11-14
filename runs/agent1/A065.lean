import ChainOfProof
open ChainOfProof

namespace Cert.A065

def cited : List Fact := [
  ⟨163, .webSearch, 1427140509975901, 1, 98, 69⟩ ]

def claim : Claim := Sets.searched 163

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A065

#print axioms Cert.A065.verified
