import ChainOfProof
open ChainOfProof

namespace Cert.A144

def cited : List Fact := [
  ⟨112, .fileModified, 1427297314552404, 1, 45, 4⟩ ]

def claim : Claim := Sets.fileModifiedAt 112

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A144

#print axioms Cert.A144.verified
