import ChainOfProof
open ChainOfProof

namespace Cert.A030

def cited : List Fact := [
  ⟨128, .webSearch, 1427133918131407, 1, 76, 69⟩ ]

def claim : Claim := Sets.searched 128

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A030

#print axioms Cert.A030.verified
