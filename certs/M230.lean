import ChainOfProof
open ChainOfProof

namespace Cert.M230

def cited : List Fact := [
  ⟨501, .systemSetting, 1427034866000000, 1000000, 256, 0⟩,
  ⟨502, .systemSetting, 1427037713122990, 1, 257, 258⟩,
  ⟨503, .systemSetting, 1427037713122990, 1, 259, 260⟩,
  ⟨504, .systemSetting, 1427037713122990, 1, 261, 262⟩,
  ⟨505, .systemSetting, 1427279593129919, 1, 263, 264⟩,
  ⟨506, .systemSetting, 1427279665685648, 1, 265, 266⟩,
  ⟨507, .systemSetting, 1427297091250805, 1, 263, 267⟩,
  ⟨508, .systemSetting, 1427297091250805, 1, 268, 269⟩,
  ⟨509, .systemSetting, 1427297091250805, 1, 270, 271⟩,
  ⟨510, .systemSetting, 1427297091250805, 1, 272, 273⟩,
  ⟨511, .systemSetting, 1427297465232008, 1, 274, 0⟩,
  ⟨512, .systemSetting, 1794614400000000, 1, 275, 276⟩,
  ⟨513, .systemSetting, 1794614400000000, 1, 275, 277⟩,
  ⟨514, .systemSetting, 1794614400000000, 1, 278, 279⟩,
  ⟨515, .systemSetting, 1794614400000000, 1, 278, 280⟩,
  ⟨516, .systemSetting, 1794614400000000, 1, 278, 281⟩,
  ⟨517, .systemSetting, 1794614400000000, 1, 278, 282⟩,
  ⟨518, .systemSetting, 1794614400000000, 1, 283, 284⟩,
  ⟨519, .systemSetting, 1794614400000000, 1, 283, 285⟩,
  ⟨520, .systemSetting, 1794614400000000, 1, 283, 286⟩,
  ⟨521, .systemSetting, 1794614400000000, 1, 283, 287⟩ ]

def claim : Claim := .both (Sets.settingRecorded 501) (.both (Sets.settingRecorded 502) (.both (Sets.settingRecorded 503) (.both (Sets.settingRecorded 504) (.both (Sets.settingRecorded 505) (.both (Sets.settingRecorded 506) (.both (Sets.settingRecorded 507) (.both (Sets.settingRecorded 508) (.both (Sets.settingRecorded 509) (.both (Sets.settingRecorded 510) (.both (Sets.settingRecorded 511) (.both (Sets.settingRecorded 512) (.both (Sets.settingRecorded 513) (.both (Sets.settingRecorded 514) (.both (Sets.settingRecorded 515) (.both (Sets.settingRecorded 516) (.both (Sets.settingRecorded 517) (.both (Sets.settingRecorded 518) (.both (Sets.settingRecorded 519) (.both (Sets.settingRecorded 520) (Sets.settingRecorded 521))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M230

#print axioms Cert.M230.verified
