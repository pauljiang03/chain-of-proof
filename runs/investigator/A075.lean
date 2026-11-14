import ChainOfProof
open ChainOfProof

namespace Cert.A075

def cited : List Fact := [
  ⟨274, .webSearch, 1427144117475595, 1, 161, 126⟩ ]

def claim : Claim := Sets.searched 274

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A075

#print axioms Cert.A075.verified
