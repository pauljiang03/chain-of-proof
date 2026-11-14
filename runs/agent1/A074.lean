import ChainOfProof
open ChainOfProof

namespace Cert.A074

def cited : List Fact := [
  ⟨172, .webSearch, 1427144026658464, 1, 102, 70⟩ ]

def claim : Claim := Sets.searched 172

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A074

#print axioms Cert.A074.verified
