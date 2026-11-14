import ChainOfProof
open ChainOfProof

namespace Cert.A044

def cited : List Fact := [
  ⟨142, .webSearch, 1427134171496372, 1, 82, 70⟩ ]

def claim : Claim := Sets.searched 142

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A044

#print axioms Cert.A044.verified
