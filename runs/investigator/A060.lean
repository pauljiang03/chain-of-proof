import ChainOfProof
open ChainOfProof

namespace Cert.A060

def cited : List Fact := [
  ⟨259, .webSearch, 1427140509975901, 1, 154, 125⟩ ]

def claim : Claim := Sets.searched 259

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A060

#print axioms Cert.A060.verified
