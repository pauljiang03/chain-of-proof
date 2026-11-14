import ChainOfProof
open ChainOfProof

namespace Cert.A018

def cited : List Fact := [
  ⟨116, .webSearch, 1427038079597811, 1, 71, 69⟩ ]

def claim : Claim := Sets.searched 116

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A018

#print axioms Cert.A018.verified
