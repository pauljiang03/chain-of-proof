import ChainOfProof
open ChainOfProof

namespace Cert.A050

def cited : List Fact := [
  ⟨148, .webSearch, 1427134417494371, 1, 88, 70⟩ ]

def claim : Claim := Sets.searched 148

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A050

#print axioms Cert.A050.verified
