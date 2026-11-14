import ChainOfProof
open ChainOfProof

namespace Cert.A027

def cited : List Fact := [
  ⟨995, .programInstalled, 1427295451895803, 1, 355, 356⟩,
  ⟨1409, .programRun, 1427295014393805, 1, 966, 967⟩,
  ⟨1449, .programRun, 1427296348735000, 1, 763, 1018⟩,
  ⟨1451, .programRun, 1427296410777005, 1, 1021, 1022⟩ ]

def claim : Claim := .both (Sets.programInstalledAt 995) (.both (Sets.programRan 1409) (.both (Sets.programRan 1449) (Sets.programRan 1451)))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A027

#print axioms Cert.A027.verified
