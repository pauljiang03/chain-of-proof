import ChainOfProof
open ChainOfProof

namespace Cert.M242

def cited : List Fact := [
  ⟨910, .programInstalled, 1426996800000000, 86400000000, 338, 322⟩,
  ⟨911, .programInstalled, 1426996800000000, 86400000000, 339, 322⟩,
  ⟨912, .programInstalled, 1426996800000000, 86400000000, 340, 322⟩,
  ⟨913, .programInstalled, 1426996800000000, 86400000000, 341, 322⟩,
  ⟨914, .programInstalled, 1426996800000000, 86400000000, 342, 322⟩,
  ⟨915, .programInstalled, 1426996800000000, 86400000000, 343, 322⟩,
  ⟨916, .programInstalled, 1426996800000000, 86400000000, 344, 322⟩,
  ⟨917, .programInstalled, 1427036459000000, 1000000, 337, 322⟩,
  ⟨918, .programInstalled, 1427036459300055, 1, 337, 322⟩,
  ⟨919, .programInstalled, 1427036461000000, 1000000, 338, 322⟩,
  ⟨920, .programInstalled, 1427036461296858, 1, 338, 322⟩,
  ⟨921, .programInstalled, 1427036462000000, 1000000, 321, 322⟩,
  ⟨922, .programInstalled, 1427036462000000, 1000000, 323, 322⟩,
  ⟨923, .programInstalled, 1427036462217260, 1, 321, 322⟩,
  ⟨924, .programInstalled, 1427036462778860, 1, 323, 322⟩,
  ⟨925, .programInstalled, 1427036463000000, 1000000, 327, 322⟩,
  ⟨926, .programInstalled, 1427036463683662, 1, 327, 322⟩,
  ⟨927, .programInstalled, 1427036464000000, 1000000, 336, 322⟩,
  ⟨928, .programInstalled, 1427036464338863, 1, 336, 322⟩,
  ⟨929, .programInstalled, 1427036465820868, 1, 328, 322⟩,
  ⟨930, .programInstalled, 1427036466000000, 1000000, 328, 322⟩,
  ⟨931, .programInstalled, 1427036467000000, 1000000, 325, 322⟩,
  ⟨932, .programInstalled, 1427036467334068, 1, 325, 322⟩,
  ⟨933, .programInstalled, 1427036469000000, 1000000, 341, 322⟩,
  ⟨934, .programInstalled, 1427036469206072, 1, 341, 322⟩,
  ⟨935, .programInstalled, 1427036470000000, 1000000, 342, 322⟩,
  ⟨936, .programInstalled, 1427036470157673, 1, 342, 322⟩,
  ⟨937, .programInstalled, 1427036471000000, 1000000, 324, 322⟩,
  ⟨938, .programInstalled, 1427036471608477, 1, 324, 322⟩,
  ⟨939, .programInstalled, 1427036472000000, 1000000, 326, 322⟩,
  ⟨940, .programInstalled, 1427036472466478, 1, 326, 322⟩,
  ⟨941, .programInstalled, 1427036473000000, 1000000, 339, 322⟩,
  ⟨942, .programInstalled, 1427036473683279, 1, 339, 322⟩,
  ⟨943, .programInstalled, 1427036474000000, 1000000, 335, 322⟩,
  ⟨944, .programInstalled, 1427036474775282, 1, 335, 322⟩,
  ⟨945, .programInstalled, 1427036490858910, 1, 344, 322⟩,
  ⟨946, .programInstalled, 1427036491000000, 1000000, 344, 322⟩,
  ⟨947, .programInstalled, 1427036491857311, 1, 334, 322⟩,
  ⟨948, .programInstalled, 1427036492000000, 1000000, 333, 322⟩,
  ⟨949, .programInstalled, 1427036492000000, 1000000, 334, 322⟩ ]

def claim : Claim := .both (Sets.programInstalledAt 910) (.both (Sets.programInstalledAt 911) (.both (Sets.programInstalledAt 912) (.both (Sets.programInstalledAt 913) (.both (Sets.programInstalledAt 914) (.both (Sets.programInstalledAt 915) (.both (Sets.programInstalledAt 916) (.both (Sets.programInstalledAt 917) (.both (Sets.programInstalledAt 918) (.both (Sets.programInstalledAt 919) (.both (Sets.programInstalledAt 920) (.both (Sets.programInstalledAt 921) (.both (Sets.programInstalledAt 922) (.both (Sets.programInstalledAt 923) (.both (Sets.programInstalledAt 924) (.both (Sets.programInstalledAt 925) (.both (Sets.programInstalledAt 926) (.both (Sets.programInstalledAt 927) (.both (Sets.programInstalledAt 928) (.both (Sets.programInstalledAt 929) (.both (Sets.programInstalledAt 930) (.both (Sets.programInstalledAt 931) (.both (Sets.programInstalledAt 932) (.both (Sets.programInstalledAt 933) (.both (Sets.programInstalledAt 934) (.both (Sets.programInstalledAt 935) (.both (Sets.programInstalledAt 936) (.both (Sets.programInstalledAt 937) (.both (Sets.programInstalledAt 938) (.both (Sets.programInstalledAt 939) (.both (Sets.programInstalledAt 940) (.both (Sets.programInstalledAt 941) (.both (Sets.programInstalledAt 942) (.both (Sets.programInstalledAt 943) (.both (Sets.programInstalledAt 944) (.both (Sets.programInstalledAt 945) (.both (Sets.programInstalledAt 946) (.both (Sets.programInstalledAt 947) (.both (Sets.programInstalledAt 948) (Sets.programInstalledAt 949)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M242

#print axioms Cert.M242.verified
