import ChainOfProof
open ChainOfProof

namespace Cert.A091

def cited : List Fact := [
  ⟨259, .webSearch, 1427140509975901, 1, 154, 125⟩,
  ⟨260, .webSearch, 1427140564087328, 1, 155, 125⟩ ]

def claim : Claim := .both (Sets.searched 259) (Sets.searched 260)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A091

#print axioms Cert.A091.verified
