import ChainOfProof
open ChainOfProof

namespace Cert.A039

def cited : List Fact := [
  ⟨238, .webSearch, 1427134171496372, 1, 138, 126⟩ ]

def claim : Claim := Sets.searched 238

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A039

#print axioms Cert.A039.verified
