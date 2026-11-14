import ChainOfProof
open ChainOfProof

namespace Cert.A171

def cited : List Fact := [
  ⟨208, .fileDeleted, 1427227902851000, 1, 123, 4⟩ ]

def claim : Claim := Sets.fileDeletedAt 208

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A171

#print axioms Cert.A171.verified
