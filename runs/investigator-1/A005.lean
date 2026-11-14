import ChainOfProof
open ChainOfProof

namespace Cert.A005

def cited : List Fact := [
  ⟨650, .sessionEvent, 1427039624310112, 1, 297, 291⟩,
  ⟨685, .sessionEvent, 1427039906374947, 1, 301, 291⟩,
  ⟨659, .sessionEvent, 1427039757259062, 1, 297, 293⟩,
  ⟨684, .sessionEvent, 1427039876376093, 1, 301, 293⟩ ]

def claim : Claim := .both (Sets.sessionRecorded 650) (.both (Sets.sessionRecorded 685) (.both (Sets.sessionRecorded 659) (Sets.sessionRecorded 684)))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A005

#print axioms Cert.A005.verified
