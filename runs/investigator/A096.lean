import ChainOfProof
open ChainOfProof

namespace Cert.A096

def cited : List Fact := [
  ⟨239, .webSearch, 1427134203820419, 1, 139, 126⟩,
  ⟨318, .tag, 1794614400000000, 1, 139, 195⟩ ]

def claim : Claim := Sets.tagged 239 .obj 318 195

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A096

#print axioms Cert.A096.verified
