import ChainOfProof
open ChainOfProof

namespace Cert.A049

def cited : List Fact := [
  ⟨368, .emailSent, 1427131767000000, 1000000, 205, 206⟩,
  ⟨369, .emailSent, 1427136271719000, 1000000, 207, 208⟩,
  ⟨370, .emailSent, 1427138098000000, 1000000, 209, 206⟩,
  ⟨371, .emailSent, 1427138441000000, 1000000, 210, 206⟩,
  ⟨372, .emailSent, 1427138782000000, 1000000, 211, 206⟩,
  ⟨373, .emailSent, 1427138825282000, 1000000, 212, 208⟩,
  ⟨374, .emailSent, 1427143279000000, 1000000, 213, 206⟩,
  ⟨375, .emailSent, 1427203557000000, 1000000, 214, 206⟩,
  ⟨376, .emailSent, 1427204110365000, 1000000, 215, 208⟩,
  ⟨377, .emailSent, 1427225642435000, 1000000, 216, 208⟩,
  ⟨378, .emailSent, 1427231109679000, 1000000, 217, 208⟩ ]

def census : Census := .total .emailSent 11

theorem verified : counts cited census = true := by decide +kernel

end Cert.A049

#print axioms Cert.A049.verified
