import ChainOfProof
open ChainOfProof

namespace Cert.A148

def cited : List Fact := [
  ⟨177, .fileModified, 1422046030000000, 2000000, 92, 69⟩ ]

def claim : Claim := Sets.fileModifiedAt 177

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A148

#print axioms Cert.A148.verified
