import ChainOfProof
open ChainOfProof

namespace Cert.M244

def cited : List Fact := [
  ⟨990, .programInstalled, 1427295126105404, 1, 357, 358⟩,
  ⟨991, .programInstalled, 1427295232000000, 1000000, 357, 358⟩,
  ⟨992, .programInstalled, 1427295246693405, 1, 359, 358⟩,
  ⟨993, .programInstalled, 1427295273931004, 1, 359, 358⟩,
  ⟨994, .programInstalled, 1427295290000000, 1000000, 359, 358⟩,
  ⟨995, .programInstalled, 1427295451895803, 1, 355, 356⟩,
  ⟨996, .programInstalled, 1427295469000000, 1000000, 355, 356⟩ ]

def claim : Claim := .both (Sets.programInstalledAt 990) (.both (Sets.programInstalledAt 991) (.both (Sets.programInstalledAt 992) (.both (Sets.programInstalledAt 993) (.both (Sets.programInstalledAt 994) (.both (Sets.programInstalledAt 995) (Sets.programInstalledAt 996))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M244

#print axioms Cert.M244.verified
