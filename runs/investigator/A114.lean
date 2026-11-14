import ChainOfProof
open ChainOfProof

namespace Cert.A114

def cited : List Fact := [
  ⟨241, .webSearch, 1427134310582693, 1, 141, 126⟩,
  ⟨360, .tag, 1794614400000000, 1, 141, 195⟩ ]

def claim : Claim := Sets.tagged 241 .obj 360 195

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A114

#print axioms Cert.A114.verified
