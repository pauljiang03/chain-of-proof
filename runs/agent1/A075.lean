import ChainOfProof
open ChainOfProof

namespace Cert.A075

def cited : List Fact := [
  ⟨173, .webSearch, 1427144108521080, 1, 103, 70⟩ ]

def claim : Claim := Sets.searched 173

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A075

#print axioms Cert.A075.verified
