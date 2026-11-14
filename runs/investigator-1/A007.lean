import ChainOfProof
open ChainOfProof

namespace Cert.A007

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

def census : Census := .distinct .accountSeen .obj 8

theorem verified : counts cited census = true := by decide +kernel

end Cert.A007

#print axioms Cert.A007.verified
