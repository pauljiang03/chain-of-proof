import ChainOfProof
open ChainOfProof

namespace Cert.A001

def cited : List Fact := [
  ⟨502, .systemSetting, 1427037713122990, 1, 257, 258⟩,
  ⟨503, .systemSetting, 1427037713122990, 1, 259, 260⟩,
  ⟨505, .systemSetting, 1427279593129919, 1, 263, 264⟩,
  ⟨504, .systemSetting, 1427037713122990, 1, 261, 262⟩,
  ⟨506, .systemSetting, 1427279665685648, 1, 265, 266⟩,
  ⟨501, .systemSetting, 1427034866000000, 1000000, 256, 0⟩,
  ⟨510, .systemSetting, 1427297091250805, 1, 272, 273⟩,
  ⟨511, .systemSetting, 1427297465232008, 1, 274, 0⟩ ]

def claim : Claim := .both (Sets.settingRecorded 502) (.both (Sets.settingRecorded 503) (.both (Sets.settingRecorded 505) (.both (Sets.settingRecorded 504) (.both (Sets.settingRecorded 506) (.both (Sets.settingRecorded 501) (.both (Sets.settingRecorded 510) (Sets.settingRecorded 511)))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A001

#print axioms Cert.A001.verified
