import ChainOfProof
open ChainOfProof

namespace Cert.A207

def cited : List Fact := [
  ⟨119, .fileCreated, 1427205612590000, 10000, 103, 69⟩,
  ⟨167, .fileModified, 1420491668000000, 2000000, 103, 69⟩ ]

def claim : Claim := Sets.copiedHere 119 167

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A207

#print axioms Cert.A207.verified
