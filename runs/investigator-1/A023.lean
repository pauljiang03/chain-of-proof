import ChainOfProof
open ChainOfProof

namespace Cert.A023

def cited : List Fact := [
  ⟨496, .volumeOnDevice, 1794614400000000, 1, 1, 19⟩,
  ⟨497, .volumeOnDevice, 1794614400000000, 1, 2, 253⟩,
  ⟨498, .volumeOnDevice, 1794614400000000, 1, 249, 40⟩ ]

def census : Census := .totalWith .volumeOnDevice .aux 31 0

theorem verified : counts cited census = true := by decide +kernel

end Cert.A023

#print axioms Cert.A023.verified
