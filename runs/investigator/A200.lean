import ChainOfProof
open ChainOfProof

namespace Cert.A200

def cited : List Fact := [
  ⟨112, .fileCreated, 1427205579710000, 10000, 96, 69⟩,
  ⟨156, .fileModified, 1417459826000000, 2000000, 96, 69⟩ ]

def claim : Claim := Sets.copiedHere 112 156

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A200

#print axioms Cert.A200.verified
