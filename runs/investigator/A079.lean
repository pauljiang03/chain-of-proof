import ChainOfProof
open ChainOfProof

namespace Cert.A079

def cited : List Fact := [
  ⟨278, .webSearch, 1427144129265612, 1, 156, 126⟩ ]

def claim : Claim := Sets.searched 278

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A079

#print axioms Cert.A079.verified
