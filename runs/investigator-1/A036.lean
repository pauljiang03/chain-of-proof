import ChainOfProof
open ChainOfProof

namespace Cert.A036

def cited : List Fact := [
  ⟨333, .webSearch, 1427140509975901, 1, 188, 159⟩,
  ⟨334, .webSearch, 1427140564087328, 1, 189, 159⟩ ]

def claim : Claim := .both (Sets.searched 333) (Sets.searched 334)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A036

#print axioms Cert.A036.verified
