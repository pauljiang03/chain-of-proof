import ChainOfProof
open ChainOfProof

namespace Cert.A149

def cited : List Fact := [
  ⟨85, .fileCreated, 1427222920734358, 1, 44, 4⟩,
  ⟨111, .fileModified, 1427223570611170, 1, 44, 4⟩ ]

def claim : Claim := .before 85 111

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A149

#print axioms Cert.A149.verified
