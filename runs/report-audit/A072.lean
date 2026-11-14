import ChainOfProof
open ChainOfProof

namespace Cert.A072

def cited : List Fact := [
  ⟨294, .emailSent, 1427131767000000, 1000000, 171, 172⟩,
  ⟨295, .emailSent, 1427136271719000, 1000000, 173, 174⟩ ]

def claim : Claim := .both (Sets.emailed 294) (.both (Sets.emailed 295) (.before 294 295))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A072

#print axioms Cert.A072.verified
