import ChainOfProof
open ChainOfProof

namespace Cert.M361

def cited : List Fact := [
  ⟨496, .volumeOnDevice, 1794614400000000, 1, 1, 19⟩,
  ⟨497, .volumeOnDevice, 1794614400000000, 1, 2, 253⟩,
  ⟨498, .volumeOnDevice, 1794614400000000, 1, 249, 40⟩ ]

def census : Census := .total .volumeOnDevice 3

theorem verified : counts cited census = true := by decide +kernel

end Cert.M361

#print axioms Cert.M361.verified
