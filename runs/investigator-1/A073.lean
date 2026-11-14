import ChainOfProof
open ChainOfProof

namespace Cert.A073

def cited : List Fact := [
  ⟨379, .cdBurn, 1427226467407829, 1, 218, 219⟩,
  ⟨380, .cdBurn, 1427226467657431, 1, 220, 221⟩,
  ⟨381, .cdBurn, 1427226961607515, 1, 222, 219⟩,
  ⟨382, .cdBurn, 1427226971965935, 1, 220, 221⟩,
  ⟨383, .cdBurn, 1427228659896305, 1, 223, 219⟩,
  ⟨384, .cdBurn, 1427228686429152, 1, 220, 221⟩,
  ⟨385, .cdBurn, 1427229681619709, 1, 224, 219⟩,
  ⟨386, .cdBurn, 1427229681884909, 1, 220, 221⟩,
  ⟨387, .cdBurn, 1427230396668583, 1, 225, 226⟩ ]

def claim : Claim := .both (Sets.burnTrace 379) (.both (Sets.burnTrace 380) (.both (Sets.burnTrace 381) (.both (Sets.burnTrace 382) (.both (Sets.burnTrace 383) (.both (Sets.burnTrace 384) (.both (Sets.burnTrace 385) (.both (Sets.burnTrace 386) (Sets.burnTrace 387))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A073

#print axioms Cert.A073.verified
