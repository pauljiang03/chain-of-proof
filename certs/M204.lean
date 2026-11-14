import ChainOfProof
open ChainOfProof

namespace Cert.M204

def cited : List Fact := [
  ⟨277, .fileDeleted, 1427227902851000, 1, 152, 4⟩ ]

def claim : Claim := Sets.fileDeletedAt 277

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M204

#print axioms Cert.M204.verified
