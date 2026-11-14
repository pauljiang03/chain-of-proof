import ChainOfProof
open ChainOfProof

namespace Cert.A079

def cited : List Fact := [
  ⟨305, .cdBurn, 1427226467407829, 1, 184, 185⟩,
  ⟨306, .cdBurn, 1427226467657431, 1, 186, 187⟩,
  ⟨307, .cdBurn, 1427226961607515, 1, 188, 185⟩,
  ⟨308, .cdBurn, 1427226971965935, 1, 186, 187⟩,
  ⟨309, .cdBurn, 1427228659896305, 1, 189, 185⟩,
  ⟨310, .cdBurn, 1427228686429152, 1, 186, 187⟩,
  ⟨311, .cdBurn, 1427229681619709, 1, 190, 185⟩,
  ⟨312, .cdBurn, 1427229681884909, 1, 186, 187⟩ ]

def claim : Claim := .both (Sets.burnTrace 305) (.both (Sets.burnTrace 306) (.both (Sets.burnTrace 307) (.both (Sets.burnTrace 308) (.both (Sets.burnTrace 309) (.both (Sets.burnTrace 310) (.both (Sets.burnTrace 311) (Sets.burnTrace 312)))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A079

#print axioms Cert.A079.verified
