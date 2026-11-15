import ChainOfProof
open ChainOfProof

namespace Cert.N1

def cited : List Fact := [
  ⟨4512, .usbInsert, 1427119200000000, 1, 101, 0, ⟨0, 0, 0, 0, 0, 0, 0, 0, 0, 0⟩⟩,
  ⟨4513, .volumeMount, 1427119201000000, 1, 101, 88, ⟨0, 0, 0, 0, 0, 0, 0, 0, 0, 0⟩⟩,
  ⟨4600, .lnkTarget, 1427120900000000, 1, 913, 88, ⟨0, 0, 0, 0, 0, 0, 0, 0, 0, 0⟩⟩,
  ⟨9001, .tag, 1794636000000000, 1, 913, 50, ⟨0, 0, 0, 0, 0, 0, 0, 0, 0, 0⟩⟩,
  ⟨9002, .tag, 1794636000000000, 1, 101, 51, ⟨0, 0, 0, 0, 0, 0, 0, 0, 0, 0⟩⟩,
  ⟨3100, .webSearch, 1427119000000000, 1, 700, 0, ⟨0, 0, 0, 0, 0, 0, 0, 0, 0, 0⟩⟩ ]

def claim : Claim := .both (Sets.usbMountedAs 4512 4513) (.both (Sets.openedFromMount 4600 4513) (.both (Sets.tagged 4600 .obj 9001 50) (.both (Sets.tagged 4512 .obj 9002 51) (.before 3100 4512))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.N1

#print axioms Cert.N1.verified
