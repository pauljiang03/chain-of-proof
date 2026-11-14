import ChainOfProof
open ChainOfProof

namespace Cert.A047

def cited : List Fact := [
  ⟨368, .emailSent, 1427131767000000, 1000000, 205, 206⟩,
  ⟨369, .emailSent, 1427136271719000, 1000000, 207, 208⟩,
  ⟨370, .emailSent, 1427138098000000, 1000000, 209, 206⟩,
  ⟨371, .emailSent, 1427138441000000, 1000000, 210, 206⟩,
  ⟨372, .emailSent, 1427138782000000, 1000000, 211, 206⟩,
  ⟨373, .emailSent, 1427138825282000, 1000000, 212, 208⟩ ]

def claim : Claim := .both (Sets.emailed 368) (.both (Sets.emailed 369) (.both (Sets.emailed 370) (.both (Sets.emailed 371) (.both (Sets.emailed 372) (Sets.emailed 373)))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A047

#print axioms Cert.A047.verified
