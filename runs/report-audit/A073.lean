import ChainOfProof
open ChainOfProof

namespace Cert.A073

def cited : List Fact := [
  ⟨296, .emailSent, 1427138098000000, 1000000, 175, 172⟩,
  ⟨297, .emailSent, 1427138441000000, 1000000, 176, 172⟩ ]

def claim : Claim := .both (Sets.emailed 296) (Sets.emailed 297)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A073

#print axioms Cert.A073.verified
