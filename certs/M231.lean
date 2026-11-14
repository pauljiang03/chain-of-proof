import ChainOfProof
open ChainOfProof

namespace Cert.M231

def cited : List Fact := [
  ⟨522, .accountSeen, 1427034834422602, 1, 262, 288⟩,
  ⟨523, .accountSeen, 1427034834422602, 1, 262, 288⟩,
  ⟨524, .accountSeen, 1427039301326138, 1, 289, 290⟩,
  ⟨525, .accountSeen, 1427039514524311, 1, 291, 288⟩,
  ⟨526, .accountSeen, 1427039514524311, 1, 291, 288⟩,
  ⟨527, .accountSeen, 1427039550742777, 1, 292, 288⟩,
  ⟨528, .accountSeen, 1427039550742777, 1, 292, 288⟩,
  ⟨529, .accountSeen, 1427039581900034, 1, 293, 288⟩,
  ⟨530, .accountSeen, 1427039581900034, 1, 293, 288⟩,
  ⟨531, .accountSeen, 1427141132279000, 1000, 294, 189⟩,
  ⟨532, .accountSeen, 1427279602864338, 1, 295, 288⟩,
  ⟨533, .accountSeen, 1427279602864338, 1, 296, 288⟩,
  ⟨534, .accountSeen, 1427295641025204, 1, 289, 290⟩,
  ⟨535, .accountSeen, 1427296896782000, 1000, 294, 189⟩ ]

def claim : Claim := .both (Sets.accountRecorded 522) (.both (Sets.accountRecorded 523) (.both (Sets.accountRecorded 524) (.both (Sets.accountRecorded 525) (.both (Sets.accountRecorded 526) (.both (Sets.accountRecorded 527) (.both (Sets.accountRecorded 528) (.both (Sets.accountRecorded 529) (.both (Sets.accountRecorded 530) (.both (Sets.accountRecorded 531) (.both (Sets.accountRecorded 532) (.both (Sets.accountRecorded 533) (.both (Sets.accountRecorded 534) (Sets.accountRecorded 535)))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M231

#print axioms Cert.M231.verified
