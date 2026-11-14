import ChainOfProof
open ChainOfProof

namespace Cert.A085

def cited : List Fact := [
  ⟨117, .fileCreated, 1427205584860000, 10000, 101, 69⟩,
  ⟨162, .fileModified, 1418939458000000, 2000000, 101, 69⟩ ]

def claim : Claim := Sets.copiedHere 117 162

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A085

#print axioms Cert.A085.verified
