import ChainOfProof
open ChainOfProof

namespace Cert.A152

def cited : List Fact := [
  ⟨162, .fileModified, 1418939458000000, 2000000, 101, 69⟩ ]

def claim : Claim := Sets.fileModifiedAt 162

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A152

#print axioms Cert.A152.verified
