import ChainOfProof
open ChainOfProof

namespace Cert.A101

def cited : List Fact := [
  ⟨2309, .noteText, 1427221877057999, 1, 1431, 1432⟩ ]

def claim : Claim := Sets.noteFound 2309

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A101

#print axioms Cert.A101.verified
