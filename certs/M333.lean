import ChainOfProof
open ChainOfProof

namespace Cert.M333

def cited : List Fact := [
  ⟨12682, .shadowCopy, 1427295447293805, 1, 16117, 16118⟩ ]

def claim : Claim := Sets.shadowCopyMade 12682

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M333

#print axioms Cert.M333.verified
