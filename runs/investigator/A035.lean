import ChainOfProof
open ChainOfProof

namespace Cert.A035

def cited : List Fact := [
  ⟨234, .webSearch, 1427134079890207, 1, 136, 126⟩ ]

def claim : Claim := Sets.searched 234

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A035

#print axioms Cert.A035.verified
