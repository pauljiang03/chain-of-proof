import ChainOfProof
open ChainOfProof

namespace Cert.M280

def cited : List Fact := [
  ⟨2309, .noteText, 1427221877057999, 1, 1431, 1432⟩,
  ⟨2310, .noteText, 1427221919462999, 1, 1431, 1432⟩ ]

def claim : Claim := .both (Sets.noteFound 2309) (Sets.noteFound 2310)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M280

#print axioms Cert.M280.verified
