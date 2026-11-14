import ChainOfProof
open ChainOfProof

namespace Cert.A089

def cited : List Fact := [
  ⟨243, .webSearch, 1427134400892344, 1, 143, 126⟩,
  ⟨244, .webSearch, 1427134417494371, 1, 144, 126⟩ ]

def claim : Claim := .both (Sets.searched 243) (Sets.searched 244)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A089

#print axioms Cert.A089.verified
