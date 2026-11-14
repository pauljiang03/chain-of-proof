import ChainOfProof
open ChainOfProof

namespace Cert.A057

def cited : List Fact := [
  ⟨108, .fileCreated, 1427205567120000, 10000, 92, 69⟩,
  ⟨177, .fileModified, 1422046030000000, 2000000, 92, 69⟩ ]

def claim : Claim := Sets.copiedHere 108 177

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A057

#print axioms Cert.A057.verified
