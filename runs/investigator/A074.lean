import ChainOfProof
open ChainOfProof

namespace Cert.A074

def cited : List Fact := [
  ⟨273, .webSearch, 1427144117465595, 1, 161, 126⟩ ]

def claim : Claim := Sets.searched 273

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A074

#print axioms Cert.A074.verified
