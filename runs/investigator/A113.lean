import ChainOfProof
open ChainOfProof

namespace Cert.A113

def cited : List Fact := [
  ⟨227, .webSearch, 1427133948655159, 1, 133, 125⟩,
  ⟨359, .tag, 1794614400000000, 1, 133, 195⟩ ]

def claim : Claim := Sets.tagged 227 .obj 359 195

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A113

#print axioms Cert.A113.verified
