import ChainOfProof
open ChainOfProof

namespace Cert.A113

def cited : List Fact := [
  ⟨259, .webSearch, 1427140509975901, 1, 154, 125⟩ ]

def claim : Claim := Sets.searched 259

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A113

#print axioms Cert.A113.verified
