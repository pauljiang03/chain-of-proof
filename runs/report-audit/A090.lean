import ChainOfProof
open ChainOfProof

namespace Cert.A090

def cited : List Fact := [
  ⟨247, .webSearch, 1427134490369135, 1, 146, 125⟩,
  ⟨248, .webSearch, 1427134544517540, 1, 147, 125⟩,
  ⟨249, .webSearch, 1427134615783075, 1, 148, 125⟩,
  ⟨250, .webSearch, 1427134634631105, 1, 149, 125⟩,
  ⟨251, .webSearch, 1427134690237438, 1, 150, 125⟩,
  ⟨253, .webSearch, 1427134710872763, 1, 151, 125⟩,
  ⟨256, .webSearch, 1427134743860449, 1, 152, 125⟩ ]

def claim : Claim := .both (Sets.searched 247) (.both (Sets.searched 248) (.both (Sets.searched 249) (.both (Sets.searched 250) (.both (Sets.searched 251) (.both (Sets.searched 253) (Sets.searched 256))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A090

#print axioms Cert.A090.verified
