import ChainOfProof
open ChainOfProof

namespace Cert.A104

def cited : List Fact := [
  ⟨256, .webSearch, 1427134743860449, 1, 152, 125⟩,
  ⟨350, .tag, 1794614400000000, 1, 152, 195⟩ ]

def claim : Claim := Sets.tagged 256 .obj 350 195

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A104

#print axioms Cert.A104.verified
