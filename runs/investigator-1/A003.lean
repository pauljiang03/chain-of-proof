import ChainOfProof
open ChainOfProof

namespace Cert.A003

def cited : List Fact := [
  ⟨524, .accountSeen, 1427039301326138, 1, 289, 290⟩,
  ⟨531, .accountSeen, 1427141132279000, 1000, 294, 189⟩ ]

def claim : Claim := .both (Sets.accountRecorded 524) (Sets.accountRecorded 531)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A003

#print axioms Cert.A003.verified
