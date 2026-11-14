import ChainOfProof
open ChainOfProof

namespace Cert.A051

def cited : List Fact := [
  ⟨149, .webSearch, 1427134438392908, 1, 80, 70⟩ ]

def claim : Claim := Sets.searched 149

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A051

#print axioms Cert.A051.verified
