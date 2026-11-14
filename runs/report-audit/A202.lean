import ChainOfProof
open ChainOfProof

namespace Cert.A202

def cited : List Fact := [
  ⟨303, .emailSent, 1427225642435000, 1000000, 182, 174⟩,
  ⟨321, .tag, 1794614400000000, 1, 182, 196⟩ ]

def claim : Claim := Sets.tagged 303 .obj 321 196

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A202

#print axioms Cert.A202.verified
