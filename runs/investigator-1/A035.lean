import ChainOfProof
open ChainOfProof

namespace Cert.A035

def cited : List Fact := [
  ⟨321, .webSearch, 1427134490369135, 1, 180, 159⟩,
  ⟨322, .webSearch, 1427134544517540, 1, 181, 159⟩,
  ⟨323, .webSearch, 1427134615783075, 1, 182, 159⟩,
  ⟨324, .webSearch, 1427134634631105, 1, 183, 159⟩,
  ⟨325, .webSearch, 1427134690237438, 1, 184, 159⟩,
  ⟨327, .webSearch, 1427134710872763, 1, 185, 159⟩,
  ⟨330, .webSearch, 1427134743860449, 1, 186, 159⟩ ]

def claim : Claim := .both (Sets.searched 321) (.both (Sets.searched 322) (.both (Sets.searched 323) (.both (Sets.searched 324) (.both (Sets.searched 325) (.both (Sets.searched 327) (Sets.searched 330))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A035

#print axioms Cert.A035.verified
