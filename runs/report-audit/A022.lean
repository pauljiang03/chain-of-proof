import ChainOfProof
open ChainOfProof

namespace Cert.A022

def cited : List Fact := [
  ⟨84, .fileCreated, 1427140590661442, 1, 67, 4⟩ ]

def claim : Claim := Sets.fileCreatedAt 84

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A022

#print axioms Cert.A022.verified
