import ChainOfProof
open ChainOfProof

namespace Cert.M161

def cited : List Fact := [
  ⟨295, .emailSent, 1427136271719000, 1000000, 173, 174⟩ ]

def claim : Claim := Sets.emailed 295

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M161

#print axioms Cert.M161.verified
