import ChainOfProof
open ChainOfProof

namespace Cert.M371

def cited : List Fact := [
  ⟨12682, .shadowCopy, 1427295447293805, 1, 16117, 16118⟩ ]

def census : Census := .total .shadowCopy 1

theorem verified : counts cited census = true := by decide +kernel

end Cert.M371

#print axioms Cert.M371.verified
