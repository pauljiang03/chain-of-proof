import ChainOfProof
open ChainOfProof

namespace Cert.M211

def cited : List Fact := [
  ⟨369, .emailSent, 1427136271719000, 1000000, 207, 208⟩ ]

def claim : Claim := Sets.emailed 369

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M211

#print axioms Cert.M211.verified
